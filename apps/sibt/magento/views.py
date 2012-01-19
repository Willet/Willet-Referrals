#!/usr/bin/env python

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc"

import re, urllib

from django.utils import simplejson as json
from google.appengine.api import taskqueue
from google.appengine.api import urlfetch, memcache
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app
from time import time
from urlparse import urlparse

from apps.sibt.actionss       import SIBTClickAction
from apps.app.models          import *
from apps.sibt.models         import SIBTInstance
from apps.sibt.shopify.models import SIBTShopify, get_sibt_shopify_app_by_store_id, get_or_create_sibt_shopify_app, get_sibt_shopify_app_by_store_url
from apps.link.models         import Link, get_link_by_willt_code, create_link
from apps.user.models         import get_user_by_cookie, User, get_or_create_user_by_cookie
from apps.client.models       import *
from apps.order.models        import *
from apps.stats.models        import Stats

from util.helpers             import *
from util.urihandler          import URIHandler
from util.consts              import *

class ShowBetaPage(URIHandler):
    def get(self):
        template_values = { "SIBT_SHOPIFY_API_KEY" : SIBT_SHOPIFY_API_KEY }
        
        self.response.out.write(self.render_page('beta.html', template_values))

class SIBTShopifyWelcome(URIHandler):
    def get( self ):
        client = self.get_client() # May be None
       
        # TODO: put this somewhere smarter
        token = self.request.get('t') # token
        app = get_or_create_sibt_shopify_app(client, token=token)
        
        client_email = None
        shop_owner = 'Shopify Merchant'
        if client != None:
            client_email = client.email
            shop_owner = client.merchant.get_attr('full_name')
        template_values = {
            'app': app,
            'shop_owner': shop_owner,
            'client_email': client_email
        }

        self.response.out.write( self.render_page( 'welcome.html', template_values)) 

class ShowEditPage(URIHandler):
    # Renders a app page
    def get(self):
        """
        client = self.get_client() # May be None
        # Request varZ from us
        app_id       = self.request.get( 'id' )
        error        = self.request.get( 'error' )
        error_msg    = self.request.get( 'error_msg')
        product_name = self.request.get( 'product_name' )
        target_url   = self.request.get( 'target_url' )
        share_text   = self.request.get( 'share_text' )
        
        # Request varZ from Shopify
        shopify_url  = self.request.get( 'shop' )
        shopify_sig  = self.request.get( 'signature' )
        store_token  = self.request.get( 't' )
        shopify_timestamp = self.request.get( 'timestamp' )
        pages = {
            'one': 'old',
            'two': 'current',
            'three': 'next',
            'four': 'next'
        } 
        # Init the template values with a blank app
        template_values = {
            'pages': pages,
            'app' : None,
            'has_app': False
        }
        
        # Check the Shopify stuff if they gave it to us.
        # If it fails, let's just say they aren't coming from Shopify.
        # If we don't have this info, we could be redirecting on an error
        logging.info("CHECKING SHOPIFY")
        if shopify_sig != '' and shopify_url != '':
            # Verify Shopify varZ
            s = 'shop=%st=%stimestamp=%s' % (shopify_url, store_token, shopify_timestamp)
            d = hashlib.md5( SIBT_SHOPIFY_API_SHARED_SECRET + s).hexdigest()
            logging.info('S: %s D: %s' % (shopify_sig, d))
            
            # TODO(Barbara): What the heck happened here? Shopify stopped working.
            #if shopify_sig == d: # ie. if this is valid from shopify
            logging.info("BARBARBABRBARBABRABRBABRA")

            product_name = shopify_url.split( '.' )[0].capitalize()
            
            # Ensure the 'http' is in the URL
            if 'http' not in shopify_url:
                shopify_url = 'http://%s' % shopify_url

            # Fetch the sibt app by url
            app = get_sibt_app_by_url( shopify_url )
            if app is None:
                logging.info("NO APP")
                template_values['show_guiders'] = True
                template_values['app'] = {
                    'product_name' : client.name,
                    'target_url'   : client.url,
                    'uuid': ''
                }
            else:
                template_values['app']     = app
                template_values['has_app'] = True 
                    
            template_values['shop_owner'] = client.merchant.get_attr('full_name') if client else 'Awesome Bob'

            # The Shopify check failed. Redirecting to normal site. 
            # TODO(Barbara): This might need to change in the future.
            #else:
            #    logging.info("REDIRECTING")
            #    self.redirect( '/s/edit' )
            #    return

        # Fake a app to put data in if there is an error
        if error == '1':
            template_values['error'] = 'Invalid Shopify store url.'
            template_values['app'] = { 'product_name' : product_name,
                                        'target_url'  : target_url,
                                        'share_text'  : share_text, 
                                        'store_token' : store_token,
                                        'uuid': ''
                                      }
        elif error == '2':
            template_values['error'] = 'Please don\'t leave anything blank.'
            template_values['app'] = { 'product_name' : product_name,
                                        'target_url'  : target_url,
                                        'share_text'  : share_text, 
                                        'store_token' : store_token,
                                        'uuid': ''
                                      }
        elif error == '3':
            template_values['error'] = 'There was an error with one of your inputs: %s' % error_msg
            template_values['app'] = { 'product_name' : product_name,
                                        'target_url'  : target_url,
                                        'share_text'  : share_text, 
                                        'store_token' : store_token,
                                        'uuid': ''
                                      }

        # Otherwise, 
        elif app_id != '':
            
            # Updating an existing app here:
            app = get_app_by_id( app_id )
            if app == None:
                self.redirect( '/s/edit' )
                return
            
            template_values['has_app'] = True 
            template_values['app']       = app
            template_values['analytics'] = True if app.cached_clicks_count != 0 else False

        template_values['BASE_URL']  = URL
        template_values['has_app'] = False
        self.response.out.write( self.render_page( 'edit.html', template_values)) 
        """
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

class DynamicLoader(webapp.RequestHandler):
    """When requested serves a plugin that will contain various functionality
       for sharing information about a purchase just made by one of our clients"""
    
    def get(self):
        template_values = {}
            
        is_asker = show_votes = 0
        instance = None
        other_instances = []
        asker_name = None
        
        page_url = urlparse(self.request.remote_addr)
        target   = "%s://%s%s" % (page_url.scheme, page_url.netloc, page_url.path)

        #target = self.request.headers['REFERER']

        # Grab a User and App
        shop_url = self.request.get('shop')
        if shop_url[:7] != 'http://':
            shop_url = 'http://%s' % shop_url 

        #app  = get_sibt_shopify_app_by_store_url(shop_url)
        app   = get_sibt_shopify_app_by_store_id(self.request.get('store_id'))
        event = 'SIBTShowingButton'
        
        user = get_or_create_user_by_cookie(self, app)
        if app:
            # Is User an asker for this URL?
            actions = SIBTClickAction.get_by_user_for_url(user, target)
            instance = SIBTInstance.get_by_asker_for_url(user, target)
            logging.info('trying to get instance for\nuser: %s\ntarget: %s\ninstance: %s' % (
                user,
                target,
                instance
            ))
            if instance:
                if instance.is_live:
                    is_asker   = 1
                    show_votes = 1
                    event = 'SIBTShowingResults'
                    asker_name = instance.asker.get_name_or_handle()
            else:
                # filter actions for instances that are active
                unfiltered_count = actions.count()
                instances = SIBTInstance.all()\
                    .filter('url =', target)\
                    .filter('is_live =', True)
                key_list = [instance.key() for instance in instances]
                actions = actions.filter('sibt_instance IN', key_list)
                logging.info('got %d/%d actions after filtered by keys %s' % (
                    actions.count(),
                    unfiltered_count,
                    key_list
                ))
                if actions.count() != 0:
                    instance   = actions[0].sibt_instance
                    # assume this now because of filter
                    # if instance.is_live:
                    show_votes = 1
                    event = 'SIBTShowingVote'
                    asker_name = instance.asker.get_name_or_handle()

        template_values = {
                'URL' : URL,
                'is_asker' : is_asker,
                'show_votes' : show_votes,
                
                'app' : app,
                'instance' : instance,
                'asker_name': asker_name, 
                'other_instances': other_instances,
                
                'user': user,
                'store_id' : self.request.get('store_id')
        }

        # Finally, render the JS!
        path = os.path.join('apps/sibt/templates/', 'sibt.js')
        self.response.headers.add_header('P3P', 'CP="NOI ADM DEV PSAi COM NAV OUR OTR STP IND DEM"')
        self.response.out.write(template.render(path, template_values))
        return

