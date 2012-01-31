#!/usr/bin/env python

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc"

import re, urllib

from django.utils               import simplejson as json
from google.appengine.api       import urlfetch
from google.appengine.api       import memcache
from google.appengine.api       import taskqueue 
from google.appengine.ext       import webapp
from google.appengine.ext.webapp      import template
from google.appengine.ext.webapp.util import run_wsgi_app
# from google.appengine.ext       import db
from time                       import time
from urlparse                   import urlparse

from apps.wosib.actions         import *
from apps.app.models            import *
from apps.client.shopify.models import *
from apps.link.models           import Link
from apps.link.models           import create_link
from apps.link.models           import get_link_by_willt_code
from apps.order.models          import *
from apps.product.shopify.models import ProductShopify
from apps.wosib.models           import WOSIBInstance
from apps.wosib.models           import PartialWOSIBInstance
from apps.wosib.shopify.models   import WOSIBShopify
from apps.stats.models          import Stats

from util.consts                import *
from util.helpers               import *
from util.urihandler            import URIHandler
from util.strip_html import strip_html


class ShowWOSIBButton (webapp.RequestHandler):
    """ """
    
    def get(self):
        url = self.request.get('url')

        # Finally, render the HTML!
        path = os.path.join('apps/wosib/templates/', 'wosib_button.js')
        
        template_values = {
            
        }
        
        self.response.headers.add_header('P3P', P3P_HEADER)
        self.response.out.write(template.render(path, template_values))
        return


class ShowWOSIBInstancePage (URIHandler):
    ''' Unlike the Should I Buy This app, voters do not vote on the same page
        as the asker's cart. This renders a voting page for voters to vote on
        the cart's items, stored in a "WOSIBInstance". '''
    def get (self):
        variants = [] # populate this to show product variants on design page.
        variants = ProductShopify.all().filter('variant =', 0).get()
        template_values = { 'URL'           : URL,
                            'app_uuid'      : self.request.get('app_uuid'),
                            'user_uuid'     : self.request.get('user_uuid'),
                            'instance_uuid' : self.request.get('instance_uuid'),
                            'target_url'    : self.request.get('target_url'),
                            'evnt'          : self.request.get('evnt'),
                            'variants'      : variants
                          }
        
        path = os.path.join('apps/wosib/templates/', 'vote.html')
        self.response.headers.add_header('P3P', P3P_HEADER)
        self.response.out.write(template.render(path, template_values))
        return

class WOSIBAskDynamicLoader(webapp.RequestHandler):
    """When requested serves a plugin that will contain various functionality
       for sharing information about a purchase just made by one of our clients"""
    def get(self):
        try:
            variant_ids = map(lambda x: long(x), self.request.get('variants').split(','))
        except: # if user throws in random crap in the query string, no biggie
            variant_ids = []
        
        if variant_ids: # only if variants are valid, render the page
            logging.debug ("variant_ids = %s" % variant_ids)
            variants = []
            for variant_id in variant_ids:
                its_product = ProductShopify.all().filter ('variants = ', str(variant_id)).get()
                if its_product: # could be None of Product is somehow not in DB
                    variants.append({
                        'id' : its_product.shopify_id,
                        'image' : '/static/imgs/noimage-willet.png', # its_product.images[0],
                        'title' : its_product.title,
                        'variant_id' : variant_id,
                        'product_uuid' : its_product.uuid,
                    })
                else:
                    logging.debug ("Product for variant %s not found in DB" % variant_id)
            
            store_domain  = self.request.get('store_url')
            app           = WOSIBShopify.get_by_store_url(self.request.get('store_url'))
            user          = User.get(self.request.get('user_uuid'))
            user_found    = 1 if hasattr(user, 'fb_access_token') else 0
            user_is_admin = user.is_admin() if isinstance( user , User) else False
            target        = self.request.get( 'target_url' )
            
            origin_domain = os.environ['HTTP_REFERER'] if\
            os.environ.has_key('HTTP_REFERER') else 'UNKNOWN'
    
            logging.info('target: %s' % target)
            logging.info("APP: %r" % app)# Make a new Link
            logging.info("origin_domain: %r" % origin_domain)# Make a new Link
            logging.info("user: %r" % user)# Make a new Link
            
            link = Link.create(target, app, origin_domain, user)
            
            template_values = {
                'URL' : URL,
                'app_uuid' : self.request.get('app_uuid'),
                'user_uuid' : self.request.get('user_uuid'),
                'instance_uuid' : self.request.get('instance_uuid'),
                'target_url' : self.request.get('target_url'),
                'evnt' : self.request.get('evnt'),
                'FACEBOOK_APP_ID': app.settings['facebook']['app_id'],
                'app': app,
                'willt_url': link.get_willt_url(),
                'willt_code': link.willt_url_code,
                'variants' : variants,
            }

            # Finally, render the HTML!
            path = os.path.join('apps/wosib/templates/', 'ask.html')

            self.response.headers.add_header('P3P', P3P_HEADER)
            self.response.out.write(template.render(path, template_values))
        return

class WOSIBVoteDynamicLoader(webapp.RequestHandler):
    """Serves a plugin where people can vote on a purchase"""
    def get(self):
        template_values = {}
        user   = User.get(self.request.get('user_uuid'))
        products = [] # if no products... what render?
        link   = None
        app    = None

        instance = WOSIBInstance.get_by_uuid(self.request.get('instance_uuid'))
        try:
            # get instance by instance_uuid
            assert(instance is not None)
        except:
            try:
                logging.info('trying to get instance for code: %s' % self.request.get('willt_code'))
                app  = get_sibt_shopify_app_by_store_id(self.request.get('store_id'))
                link = get_link_by_willt_code(self.request.get('willt_code'))
                
                if link is None:
                    # no willt code, asker probably came back to page with
                    # no hash code
                    link = Link.all()\
                            .filter('user =', user)\
                            .filter('target_url =', target)\
                            .filter('app_ =', app)\
                            .get()
                    logging.info('got link by page_url %s: %s' % (target, link))
                instance = link.sibt_instance.get()
                assert(instance is not None)
            except:
                try:
                    # get instance by asker
                    instance = SIBTInstance.get_by_asker_for_url(user, target)
                    assert(instance is not None)
                except:
                    try:
                        # ugh, get the instance by actions ...
                        instances = SIBTInstance.all(key_onlys=True)\
                            .filter('url =', target)\
                            .filter('is_live =', True)\
                            .fetch(100)
                        key_list = [instance.id_or_name() for instance in instances]
                        action = SIBTClickAction.get_for_instance(app, user, target, key_list)
                        if action:
                            instance = action.sibt_instance
                            logging.info('no link, got action %s and instance %s' % (action, instance))
                        assert(instance is not None)
                    except:
                        logging.error('failed to get instance', exc_info=True)

        logging.info("Did we get an instance? %s" % instance.uuid)
        
        if instance:
            if app == None:
                app = instance.app_

            name = instance.asker.get_full_name()
            is_asker = (instance.asker.key() == user.key())
            vote_action = SIBTVoteAction.get_by_app_and_instance_and_user(app, instance, user)
            
            logging.info('got vote action: %s' % vote_action)
            has_voted = (vote_action != None)
            if not instance.is_live:
                has_voted = True

            if link == None: 
                link = instance.link
            share_url = link.get_willt_url()

            if is_asker:
                SIBTShowingResultsToAsker.create(user=user, instance=instance)
                event = 'SIBTShowingResultsToAsker'
            elif has_voted:
                SIBTShowingResults.create(user=user, instance=instance)
                event = 'SIBTShowingResultsToFriend'
            else:
                SIBTShowingVote.create(user=user, instance=instance)

            product = ProductShopify.get_or_fetch(target, app.client)

            template_values = {
                    'evnt' : event,

                    'product_img': product.images,
                    'app' : app,
                    'URL': URL,
                    
                    'user': user,
                    'asker_name' : name if name != '' else "your friend",
                    'asker_pic' : instance.asker.get_attr('pic'),
                    'target_url' : target,
                    #'fb_comments_url' : '%s#code=%s' % (target, link.willt_url_code),
                    'fb_comments_url' : '%s' % (link.get_willt_url()),

                    'share_url': share_url,
                    'is_asker' : is_asker,
                    'instance' : instance,
                    'has_voted': has_voted,

                    'yesses': instance.get_yesses_count(),
                    'noes': instance.get_nos_count()
            }

            # Finally, render the HTML!
            path = os.path.join('apps/sibt/templates/', 'vote.html')
        else:
            event = 'SIBTEventOverClosingIframe'
            template_values = {
                'output': 'Vote is over'        
            }
            path = os.path.join('apps/sibt/templates/', 'close_iframe.html')

        self.response.headers.add_header('P3P', P3P_HEADER)
        self.response.out.write(template.render(path, template_values))
        return

class WOSIBShowResults(webapp.RequestHandler):
    """ Shows the results of an instance """
    def get(self):
        template_values = {
        }

        # Finally, render the HTML!
        path = os.path.join('apps/wosib/templates/', 'results.js')

        self.response.headers.add_header('P3P', P3P_HEADER)
        self.response.out.write(template.render(path, template_values))
        return


class WOSIBShowFBThanks( URIHandler ):
    """ Called to show fb_thanks.html. 
        We know the user jsut shared on FB, so create an instance etc. """
    def get(self):
        template_values = {
        }

        # Finally, render the HTML!
        path = os.path.join('apps/wosib/templates/', 'thanks.html')

        self.response.headers.add_header('P3P', P3P_HEADER)
        self.response.out.write(template.render(path, template_values))
        return

class ShowWOSIBButtonCSS (URIHandler):
    def get( self ):
        template_values = { 'URL'           : URL,
                            'app_uuid'      : self.request.get('app_uuid')}
       
        path = os.path.join('apps/wosib/templates/css/', 'wosib_user_style.css')
        self.response.headers.add_header('P3P', P3P_HEADER)
        self.response.out.write(template.render(path, template_values))
        return

class ShowWOSIBColorboxCSS (URIHandler):
    def get( self ):
        template_values = { 'URL'           : URL,
                            'app_uuid'      : self.request.get('app_uuid')}
       
        path = os.path.join('apps/wosib/templates/css/', 'colorbox.css')
        self.response.headers.add_header('P3P', P3P_HEADER)
        self.response.out.write(template.render(path, template_values))
        return

class WOSIBColorboxJSServer( URIHandler ):
    def get( self ):
        template_values = { 'URL'           : URL,
                            'app_uuid'      : self.request.get('app_uuid'),
                            'user_uuid'     : self.request.get('user_uuid'),
                            'instance_uuid' : self.request.get('instance_uuid'),
                            'target_url'    : self.request.get('target_url') }
       
        path = os.path.join('apps/wosib/templates/js/', 'jquery.colorbox.js')
        self.response.headers.add_header('P3P', P3P_HEADER)
        self.response.out.write(template.render(path, template_values))
        return

class ShowWOSIBUnloadHook (URIHandler):
    ''' Creates a local-domain iframe that allows SJAX requests to be served
        when the window unloads. (Typically, webkit browsers do not complete 
        onunload functions unless a synchronous AJAX is sent onbeforeunload, and
        in order to send synced requests, the request must be sent to the same
        domain.)'''
    def get (self):
        template_values = { 'URL'           : URL,
                            'app_uuid'      : self.request.get('app_uuid'),
                            'user_uuid'     : self.request.get('user_uuid'),
                            'instance_uuid' : self.request.get('instance_uuid'),
                            'target_url'    : self.request.get('target_url'),
                            'evnt'          : self.request.get('evnt')
                          }
        
        path = os.path.join('apps/wosib/templates/', 'onunloadhook.html')
        self.response.headers.add_header('P3P', P3P_HEADER)
        self.response.out.write(template.render(path, template_values))
        return
