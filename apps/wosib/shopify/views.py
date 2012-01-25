#!/usr/bin/env python

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc"

import datetime
import random

from django.utils import simplejson as json
from google.appengine.api import taskqueue
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
from apps.link.models         import get_link_by_willt_code
from apps.link.models         import create_link
from apps.product.shopify.models import ProductShopify
from apps.order.models        import *
from apps.stats.models        import Stats
from apps.user.models         import get_user_by_cookie
from apps.user.models         import User
from apps.user.models         import get_or_create_user_by_cookie
from apps.sibt.shopify.models import SIBTShopify
from apps.wosib.shopify.models import WOSIBShopify

from util.shopify_helpers import get_shopify_url
from util.helpers             import *
from util.urihandler          import URIHandler
from util.consts              import *

class WOSIBShopifyServeScript (webapp.RequestHandler):
    # chucks out a javascript that helps detect events and show wizards.
    def get(self):
        is_live  = is_asker = show_votes = has_voted= show_top_bar_ask = False
        instance = share_url = link = asker_name = asker_pic = product = None
        target   = bar_or_tab = ''
        willet_code = self.request.get('willt_code') # deprecated?
        shop_url    = get_shopify_url(self.request.get('store_url'))
        if not shop_url: # backup (most probably hit)
            shop_url    = get_target_url(self.request.headers.get('REFERER')) # probably ok
        logging.debug ("shop_url = %s" % shop_url)
        app         = WOSIBShopify.get_by_store_url(shop_url)
        app_sibt_cp = SIBTShopify.get_by_store_url(shop_url) # use its CSS and stuff
        event       = 'WOSIBShowingButton'

        # A tad meaningless, as target will always be store.com/cart
        if self.request.get('page_url'):
            target = get_target_url(self.request.get('page_url'))
        else:
            target = get_target_url(self.request.headers.get('REFERER'))

        user = get_or_create_user_by_cookie( self, app )

        # Try to find an instance for this { url, user }
        try:
            logging.debug ("trying app = %s" % app)
            assert(app != None)
            try:
                # Is User an asker for this URL?
                logging.info('trying to get instance for url: %s' % target)
                instance = WOSIBInstance.get_by_asker_for_url(user, target)
                assert(instance != None)
                event = 'WOSIBShowingResults'
                logging.info('got instance by user/target: %s' % instance.uuid)
            except Exception, e:
                try:
                    logging.info('trying willet_code: %s' % e)
                    link = get_link_by_willt_code(willet_code)
                    instance = link.wosib_instance.get()
                    assert(instance != None)
                    event = 'WOSIBShowingResults'
                    logging.info('got instance by willet_code: %s' % instance.uuid)
                except Exception, e:
                    try:
                        logging.info('trying actions: %s' % e)
                        instances = WOSIBInstance.all(keys_only=True)\
                            .filter('url =', target)\
                            .fetch(100)
                        key_list = [key.id_or_name() for key in instances]
                        action = WOSIBClickAction.get_for_instance(app, user, target, key_list)
                        
                        if action:
                            instance = action.wosib_instance
                            assert(instance != None)
                            logging.info('got instance by action: %s' % instance.uuid)
                            event = 'WoSIBShowingVote'
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
                
                vote_action = WOSIBVoteAction.get_by_app_and_instance_and_user(app, instance, user)
                
                logging.info('got a vote action? %s' % vote_action)
                
                has_voted = (vote_action != None)

            try:
                if link == None: 
                    link = instance.link
                share_url = link.get_willt_url()
            except Exception,e:
                logging.error("could not get share_url: %s" % e, exc_info=True)

        else:
            logging.warn("no instance!")

        # this should only happen once, can be removed at a later date
        # TODO remove this code
        if not hasattr(app, 'button_enabled'):
            app_sibt_cp.button_enabled = True
            app_sibt_cp.put()
    
        # AB-Test or not depending on if the admin is testing.
        if not user.is_admin():
            if app_sibt_cp.incentive_enabled:
                ab_test_options = [ "Which one should I buy? Let friends vote! Save $5!",
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
                
            if app_sibt_cp.overlay_enabled:
                overlay_style = ab_test( 'sibt_overlay_style', 
                                         ["_willet_overlay_button", "_willet_overlay_button2"],
                                         user = user,
                                         app  = app )
            else:
                overlay_style = "_willet_overlay_button"

            # If subsequent page viewing and we should prompt user:
            if show_top_bar_ask:
                if app_sibt_cp.top_bar_enabled and app_sibt_cp.btm_tab_enabled:
                    bar_or_tab = ab_test( 'sibt_bar_or_tab',
                                          ['bar', 'tab'],
                                          user = user,
                                          app  = app )
                    logging.info("BAR TAB? %s" % bar_or_tab )

                    AB_top_bar = 1 if bar_or_tab == "bar" else 0
                    AB_btm_tab = int(not AB_top_bar)

                elif not app_sibt_cp.top_bar_enabled and app_sibt_cp.btm_tab_enabled:
                    AB_top_bar = 1 
                    AB_btm_tab = 0
                elif app_sibt_cp.top_bar_enabled and not app_sibt_cp.btm_tab_enabled:
                    AB_top_bar = 0 
                    AB_btm_tab = 1
                else:  # both False
                    AB_top_bar = 0 
                    AB_btm_tab = 0
            else:
                AB_top_bar = AB_btm_tab = 0
        else:
            random.seed( datetime.now() )
            
            cta_button_text = "ADMIN: Unsure? Ask your friends!"
            overlay_style   = "_willet_overlay_button"
            AB_top_bar = AB_btm_tab = 1

        # a whole bunch of css bullshit!
        if app:
            logging.info("got app button css")
            app_css = app_sibt_cp.get_css()
        else:
            app_css = WOSIBShopify.get_default_css()
        
        # Grab all template values
        template_values = {
            'URL' : URL,
            'is_asker' : is_asker,
            'show_votes' : show_votes,
            'has_voted': has_voted,
            'is_live': is_live,
            'show_top_bar_ask': show_top_bar_ask,
            
            'app'            : app,
            'instance'       : instance,
            'asker_name'     : asker_name, 
            'asker_pic'      : asker_pic,

            'AB_overlay_style' : overlay_style,

            'store_url'      : shop_url,
            'store_domain'   : getattr (app_sibt_cp.client, 'domain', ''),
            'store_id'       : self.request.get('store_id'),
            'product_uuid'   : product.uuid if product else "",
            'product_title'  : product.title if product else "",
            'product_images' : product.images if product else "",
            'product_desc'   : product.description if product else "",
          
            'user': user,
            'stylesheet': 'css/colorbox.css',

            'AB_CTA_text' : cta_button_text,
            'AB_top_bar'  : AB_top_bar,
            'AB_btm_tab'  : AB_btm_tab,
            'AB_overlay'  : int(not(bar_or_tab == "bar" or bar_or_tab =="tab")) if app_sibt_cp.overlay_enabled else 0,

            'evnt' : event,
            'img_elem_selector' : "#image img", #app.img_selector,
            'heart_img' : 0,
            
            'FACEBOOK_APP_ID': app_sibt_cp.settings['facebook']['app_id'],
            'fb_redirect' : "%s%s" % (URL, url( 'ShowFBThanks' )),
            'willt_code' : link.willt_url_code if link else "",
            'app_css': app_css,
        }









        # Try to find an instance for this { url, user }
        try:
            assert(app != None)
            # Is User an asker for this URL?
            logging.info('trying to get instance for url: %s' % target)
            instance = WOSIBInstance.get_by_asker_for_url(user, target)
        except:
            logging.info('no app or no instance')

        path = os.path.join('apps/wosib/templates/', 'wosib_button.js')
        self.response.headers.add_header('P3P', P3P_HEADER)
        self.response.headers['Content-Type'] = 'text/html; charset=utf-8'
        self.response.out.write(template.render(path, template_values))
        
        return
    
    def post (self):
        self.get() # because money.
