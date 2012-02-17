#!/usr/bin/env python

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc"

import datetime
import random

from django.utils import simplejson as json
from google.appengine.api import taskqueue
from google.appengine.api import urlfetch
from google.appengine.api import memcache
from google.appengine.ext import webapp
from google.appengine.ext import db 
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app
from time import time
from urlparse import urlparse

from apps.action.models       import ButtonLoadAction
from apps.action.models       import ScriptLoadAction
from apps.app.models          import *
from apps.client.models       import *
from apps.gae_bingo.gae_bingo import ab_test
from apps.link.models         import Link
from apps.product.shopify.models import ProductShopify
from apps.order.models        import *
from apps.sibt.actions        import SIBTClickAction
from apps.sibt.actions        import SIBTVoteAction
from apps.sibt.actions import SIBTShowingButton
from apps.sibt.models         import SIBTInstance
from apps.sibt.shopify.models import SIBTShopify
from apps.user.models         import get_user_by_cookie
from apps.user.models         import User
from apps.user.models         import get_or_create_user_by_cookie
from apps.wosib.shopify.models import WOSIBShopify

from util.shopify_helpers import get_shopify_url
from util.helpers             import *
from util.urihandler          import URIHandler
from util.consts              import *

class ShowBetaPage(URIHandler):
    def get(self):
        logging.info(SHOPIFY_APPS)
        logging.info(SHOPIFY_APPS['SIBTShopify'] )
        template_values = { 'SHOPIFY_API_KEY' : SHOPIFY_APPS['SIBTShopify']['api_key'] }
        
        self.response.out.write(self.render_page('beta.html', template_values))

class SIBTShopifyWelcome(URIHandler):
    def get(self):
        logging.info('SIBTShopifyWelcome: trying to create app')
        try:
            client = self.get_client() # May be None if not authenticated
            logging.debug ('client is %s' % client)        
            token = self.request.get('t') # token
            app = SIBTShopify.get_or_create(client, token=token) # calls do_install()
            app2 = WOSIBShopify.get_or_create(client, token=token) # calls do_install()
            
            client_email = None
            shop_owner   = 'Shopify Merchant'
            shop_name    = 'Your Shopify Store'
            if client is not None and client.merchant is not None:
                client_email = client.email
                shop_owner   = client.merchant.get_attr('full_name')
                shop_name    = client.name

            # Switched to new order tracking code on Jan 16
            if app.created > datetime( 2012, 01, 16 ):
                new_order_code = 1
            else:
                new_order_code = 0
            
            template_values = {
                'app': app,
                'URL' : URL,
                'shop_name' : shop_name,
                'shop_owner': shop_owner,
                'client_email': client_email,
                'client_uuid' : client.uuid,
                'new_order_code' : new_order_code
            }

            self.response.out.write( self.render_page( 'welcome.html', template_values)) 
        except:
            logging.error('wtf: (apps/sibt/shopify)', exc_info=True)

class SIBTShopifyEditStyle(URIHandler):
    def post(self, app_uuid):
        app = SIBTShopify.get(app_uuid)
        post_vars = self.request.arguments()

        """
        client = self.get_client()
        if client.uuid != app.client.uuid:
            self.redirect('/')
        """

        if self.request.get('set_to_default'):
            logging.error('reset button')
            app.reset_css()
        else:
            css_dict = app.get_css_dict()
            for key in css_dict:
                for value in css_dict[key]:
                    lookup = '%s:%s' % (key, value)
                    #logging.info('looking for: %s' % lookup)
                    if lookup in post_vars:
                        #logging.info('found with value: %s' % 
                        #        self.request.get(lookup))
                        css_dict[key][value] = self.request.get(lookup) 

            app.set_css(css_dict)
        self.get(app_uuid, app = app)

    def get(self, app_uuid, app=None):
        if not app:
            app = SIBTShopify.get(app_uuid)

        """
        client = self.get_client()
        if client.uuid != app.client.uuid:
            self.redirect('/')
        """

        css_dict = app.get_css_dict()
        css_values = app.get_css()
        display_dict = {}
        for key in css_dict:
            # because template has issues with variables that have
            # a dash in them
            new_key = key.replace('-', '_').replace('.','_')
            #logging.warn('adding key:\n%s = %s' % (new_key, css_dict[key]))
            display_dict[new_key] = css_dict[key]

        logging.warn('css: %s' % css_values)

        template_values = {
            'css': css_values,
            'app': app,        
            'message': '',
            'ff_options': [
                'Arial,Helvetica',
            ]
        }
        template_values.update(display_dict)
        
        self.response.out.write(self.render_page('edit_style.html', template_values)) 

class ShowEditPage(URIHandler):
    def get(self):
        pass

class ShowFinishedPage(URIHandler):
    def get(self):
        app_id       = self.request.get( 'id' )
        pages = {
            'one': 'old',
            'two': 'old',
            'three': 'old',
            'four': 'current'
        } 
        # Init the template values with a blank app
        template_values = {
            'pages': pages,
            'app' : None,
            'has_app': False
        }
        app = get_app_by_id( app_id )
        if app == None:
            self.redirect( '/s/edit' )
            return
            
        template_values['has_app'] = True 
        template_values['app']       = app
        template_values['analytics'] = True if app.cached_clicks_count != 0 else False
        template_values['BASE_URL']  = URL

        self.response.out.write(
            self.render_page(
                'finished.html',
                template_values
            )
        ) 

class ShowCodePage( URIHandler ):
    def get(self):
       pass

class SIBTShopifyServeScript(webapp.RequestHandler):
    """When requested serves a plugin that will contain various functionality
       for sharing information about a purchase just made by one of our clients"""
    
    def get(self):
        is_live  = is_asker = show_votes = has_voted= show_top_bar_ask = False
        instance = share_url = link = asker_name = asker_pic = product = None
        target   = bar_or_tab = ''
        willet_code = self.request.get('willt_code') 
        shop_url    = get_shopify_url(self.request.get('store_url'))
        app         = SIBTShopify.get_by_store_url(shop_url)
        event       = 'SIBTShowingButton'

        if self.request.get('page_url'):
            target = get_target_url(self.request.get('page_url'))
        else:
            target = get_target_url(self.request.headers.get('REFERER'))

        user = get_or_create_user_by_cookie( self, app )

        # Try to find an instance for this { url, user }
        try:
            assert(app != None)
            try:
                # Is User an asker for this URL?
                logging.info('trying to get instance for url: %s' % target)
                instance = SIBTInstance.get_by_asker_for_url(user, target)
                assert(instance != None)
                event = 'SIBTShowingResults'
                logging.info('got instance by user/target: %s' % instance.uuid)
            except Exception, e:
                try:
                    logging.info('trying willet_code: %s' % e)
                    link = Link.get_by_code(willet_code)
                    instance = link.sibt_instance.get()
                    assert(instance != None)
                    event = 'SIBTShowingResults'
                    logging.info('got instance by willet_code: %s' % instance.uuid)
                except Exception, e:
                    try:
                        logging.info('trying actions: %s' % e)
                        instances = SIBTInstance.all(keys_only=True)\
                            .filter('url =', target)\
                            .fetch(100)
                        key_list = [key.id_or_name() for key in instances]
                        action = SIBTClickAction.get_for_instance(app, user, target, key_list)
                        
                        if action:
                            instance = action.sibt_instance
                            assert(instance != None)
                            logging.info('got instance by action: %s' % instance.uuid)
                            event = 'SIBTShowingVote'
                    except Exception, e:
                        logging.info('no instance available: %s' % e)
        except:
            logging.info('no app')

        # If we have an instance, figure out if 
        # a) Is User asker?
        # b) Has this User voted?
        if instance:
            is_live    = instance.is_live
            asker_name = instance.asker.get_first_name()
            asker_pic  = instance.asker.get_attr('pic')
            show_votes = True

            try:
                asker_name = asker_name.split(' ')[0]
                if not asker_name:
                    asker_name = 'I' # what?
            except:
                logging.warn('error splitting the asker name')

            is_asker = (instance.asker.key() == user.key()) 
            if not is_asker:
                logging.info('not asker, check for vote ...')
                
                vote_action = SIBTVoteAction.get_by_app_and_instance_and_user(app, instance, user)
                
                logging.info('got a vote action? %s' % vote_action)
                
                has_voted = (vote_action != None)

            try:
                if link == None: 
                    link = instance.link
                share_url = link.get_willt_url()
            except Exception,e:
                logging.error("could not get share_url: %s" % e, exc_info=True)

        elif app:
            logging.info('could not get an instance, check page views')

            tracked_urls = SIBTShowingButton.get_tracking_by_user_and_app(user, app)
            logging.info('got tracked urls')
            logging.info(tracked_urls)
            if tracked_urls.count(target) >= app.num_shows_before_tb:
                #if view_actions >= 1:# or user.is_admin():
                # user has viewed page more than once
                # show top-bar-ask
                show_top_bar_ask = True 
            product = ProductShopify.get_or_fetch(target, app.client)
        else:
            logging.warn("no app and no instance!")

        # this should only happen once, can be removed at a later date
        # TODO remove this code
        if not hasattr(app, 'button_enabled'):
            app.button_enabled = True
            app.put()

        # a whole bunch of css bullshit!
        if app:
            logging.info("got app button css")
            app_css = app.get_css()
        else:
            app_css = SIBTShopify.get_default_css()
        
        # Grab all template values
        template_values = {
            'URL'            : URL,
            'is_asker'       : is_asker,
            'show_votes'     : show_votes,
            'has_voted'      : has_voted,
            'is_live'        : is_live,
            'show_top_bar_ask' : str((show_top_bar_ask and (app.top_bar_enabled if app else True))),
            
            'app'            : app,
            'instance'       : instance,
            'asker_name'     : asker_name, 
            'asker_pic'      : asker_pic,

            'store_url'      : shop_url,
            'store_domain'   : getattr (app.client, 'domain', ''),
            'store_id'       : self.request.get('store_id'),
            'product_uuid'   : product.uuid if product else "",
            'product_title'  : product.title if product else "",
            'product_images' : product.images if product else "",
            'product_desc'   : product.description if product else "",
          
            'user': user,
            'stylesheet': '../../plugin/templates/css/colorbox.css',

            'evnt' : event,
            
            'FACEBOOK_APP_ID': app.settings['facebook']['app_id'],
            'fb_redirect' : "%s%s" % (URL, url( 'ShowFBThanks' )),
            'willt_code' : link.willt_url_code if link else "",
            'app_css': app_css,
        }

        # Store a script load action.
        # ButtonLoadAction.create( user, app, target )

        # Finally, render the JS!
        path = os.path.join('apps/sibt/templates/', 'sibt.js')
        self.response.headers.add_header('P3P', P3P_HEADER)
        self.response.headers['Content-Type'] = 'text/javascript; charset=utf-8'
        self.response.out.write(template.render(path, template_values))
        return

class SIBTShopifyServeAB (webapp.RequestHandler):
    """ Serve AB values for SIBTShopifyServeScript in a different JSON request.
        Hopes are that it speeds up button rendering.
    """
    
    def get(self):
        shop_url    = get_shopify_url(self.request.get('store_url'))
        app         = SIBTShopify.get_by_store_url(shop_url)
        user        = get_or_create_user_by_cookie( self, app )
        
        # return json format if jsonp is not set
        jsonp       = self.request.get('jsonp', False)
        if jsonp:
            jsonp = True # convert string to boolean

        # AB-Test or not depending on if the admin is testing.
        if not user.is_admin():
            if app.incentive_enabled:
                ab_test_options = [ "Not sure? Let friends vote! Save $5!",
                                    "Earn $5! Ask your friends what they think!",
                                    "Need advice? Ask your friends! Earn $5!",
                                    "Save $5 by getting advice from friends!",
                                    # Muck with visitors' intrinsic motivation:
                                    # If user expects to get nothing but gets one by surprise, he/she will much more likely repeat the same action
                                    # (enable if you like)
                                    # "Not sure? Ask your friends.", 
                                  ]
                cta_button_text = ab_test( 'sibt_incentive_text', 
                                            ab_test_options, 
                                            user = user,
                                            app  = app )
            else:
                ab_test_options = [ "Not sure? Start a vote!",
                                    "Not sure? Let friends vote!",
                                    "Need advice? Ask your friends to vote",
                                    "Need advice? Ask your friends!",
                                    "Unsure? Get advice from friends!",
                                    "Unsure? Get your friends to vote!",
                                    ]
                cta_button_text = ab_test( 'sibt_button_text6', 
                                            ab_test_options, 
                                            user = user,
                                            app  = app )
        else:
            cta_button_text = "ADMIN: Unsure? Ask your friends!"

       
        # Finally, render the JS!
        self.response.headers.add_header('P3P', P3P_HEADER)
        if jsonp: # JSONP
            self.response.headers['Content-Type'] = 'text/javascript; charset=utf-8'
            self.response.out.write ('var AB_CTA_text = "%s";' % cta_button_text)
        else: # JSON
            self.response.headers['Content-Type'] = 'application/json'
            self.response.out.write ('{ "AB_CTA_text": "%s" }' % cta_button_text)
        return

class SIBTShopifyProductDetection(webapp.RequestHandler):
    def get(self):
        """Serves up some high quality javascript that detects if our special
        div is on this page, and if so, loads the real SIBT js"""
        store_url = self.request.get('store_url')
        app       = SIBTShopify.get_by_store_url(store_url)
        user      = get_or_create_user_by_cookie( self, app )
        target    = get_target_url(self.request.headers.get('REFERER'))

        # Store a script load action.
        ScriptLoadAction.create(user, app, target)

        template_values = {
            'URL' : URL,
            'store_url': store_url,
            'user': user,
            'sibt_button_id': '_willet_shouldIBuyThisButton',
        }
        path = os.path.join('apps/sibt/templates/', 'sibt_product_detection.js')
        self.response.headers.add_header('P3P', P3P_HEADER)
        self.response.headers['Content-Type'] = 'text/html; charset=utf-8'
        self.response.out.write(template.render(path, template_values))
        
        return

