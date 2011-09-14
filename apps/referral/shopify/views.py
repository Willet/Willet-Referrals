#!/usr/bin/env python

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc"

import re, urllib

from django.utils import simplejson as json
from google.appengine.api import urlfetch, memcache
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app
from time import time

from apps.app.models import *
from apps.referral.models import get_referral_app_by_url
from apps.referral.shopify.api_wrapper import add_referree_gift_to_shopify_order
from apps.referral.shopify.models import get_shopify_app_by_id, create_referral_shopify_app
from apps.link.models import Link, get_link_by_willt_code, create_link
from apps.user.models import get_user_by_cookie, User, get_or_create_user_by_cookie
from apps.client.models import *
from apps.order.models import *
from apps.stats.models import Stats

from util.helpers import *
from util.urihandler import URIHandler
from util.consts import *

class ShowEditPage( URIHandler ):
    # Renders a app page
    def get(self):
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
        
        # Init the template values with a blank app
        template_values = { 'app' : None }
        
        # Check the Shopify stuff if they gave it to us.
        # If it fails, let's just say they aren't coming from Shopify.
        # If we don't have this info, we could be redirecting on an error
        logging.info("CHECKING SHOPIFY")
        if shopify_sig != '' and shopify_url != '':
            # Verify Shopify varZ
            s = 'shop=%st=%stimestamp=%s' % (shopify_url, store_token, shopify_timestamp)
            d = hashlib.md5( SHOPIFY_API_SHARED_SECRET + s).hexdigest()
            logging.info('S: %s D: %s' % (shopify_sig, d))
            
            # TODO(Barbara): What the heck happened here? Shopify stopped working.
            #if shopify_sig == d: # ie. if this is valid from shopify
            logging.info("BARBARBABRBARBABRABRBABRA")

            product_name = shopify_url.split( '.' )[0].capitalize()
            
            # Ensure the 'http' is in the URL
            if 'http' not in shopify_url:
                shopify_url = 'http://%s' % shopify_url

            # Fetch the referral app by url
            app = get_referral_app_by_url( shopify_url )
            if app is None:
                logging.info("NO APP")
                template_values['show_guiders'] = True
                template_values['app'] = {
                    'product_name' : client.name,
                    'target_url'   : client.url,
                    'shop_owner'   : client.merchant.full_name,
                    'uuid': ''
                }
                template_values['has_app'] = False
            else:
                template_values['app']     = app

            # The Shopify check failed. Redirecting to normal site. 
            # TODO(Barbara): This might need to change in the future.
            #else:
            #    logging.info("REDIRECTING")
            #    self.redirect( '/r/edit' )
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
                self.redirect( '/r/edit' )
                return
            
            template_values['app']       = app
            template_values['analytics'] = True if app.cached_clicks_count != 0 else False

        template_values['BASE_URL']  = URL

        self.response.out.write( self.render_page( 'edit.html', template_values)) 

class ShowCodePage( URIHandler ):
    def get(self):
        app_id = self.request.get( 'id' )
        template_values = { 'app' : None }
        
        if app_id:
            # Updating an existing app here:
            app = get_shopify_app_by_id(app_id)
            if app == None:
                self.redirect( '/account' )
                return

            template_values['app'] = app
        
        template_values['BASE_URL'] = URL

        self.response.out.write( self.render_page( 'code.html', template_values ))

class DoUpdateOrCreate( URIHandler ):
    
    def post( self ):
        client      = self.get_client() # might be None
        logging.info("CLIENT: %r:" % client)
        # Request varZ
        app_id       = self.request.get( 'uuid' )
        product_name = self.request.get( 'product_name' )
        target_url   = self.request.get( 'target_url' )
        share_text   = self.request.get( 'share_text' )
        store_token  = self.request.get( 'token' )
        
        # Error check the input!
        if product_name == '' or target_url == ''  or share_text == '':
            self.redirect( '/r/shopify/edit?id=%s&t=%s&error=2&share_text=%s&target_url=%s&product_name=%s' % (app_id, store_token, share_text, target_url, product_name) )
            return
        if not isGoodURL( target_url ):
            self.redirect( '/r/shopify/edit?id=%s&t=%s&error=1&share_text=%s&target_url=%s&product_name=%s' % (app_id, store_token, share_text, target_url, product_name) )
            return

        # If no one is logged in, make them login!
        if client is None:
            self.redirect( '/login?url=/shopify/r/edit?id=%s&t=%s&share_text=%s&target_url=%s&product_name=%s' % (app_id, store_token, share_text, target_url, product_name) )
            return
        
        # Try to grab the referral app
        referral_app = get_app_by_id( app_id )
        
        # If app doesn't exist,
        if referral_app == None:
        
            # Create a new one!
            referral_app = create_referral_shopify_app( client, share_text )

        # Otherwise, update the existing app.
        else:
            referral_app.share_text = share_text
            referral_app.put()
        
        self.redirect( '/r/shopify/code?id=%s' % referral_app.uuid )

class DynamicLoader(webapp.RequestHandler):
    """When requested serves a plugin that will contain various functionality
       for sharing information about a purchase just made by one of our clients"""
    
    def get(self, input_path):
        logging.info('Token %s' % self.request.get('order_token'))
        template_values = {}
        rq_vars = get_request_variables(['store_id', 'order_token', 'demo'], self)
        origin_domain = os.environ['HTTP_REFERER'] if\
            os.environ.has_key('HTTP_REFERER') else 'UNKNOWN'

        is_demo = (rq_vars['demo'] != '')
            
        # Grab a User if we have a cookie!
        user       = get_or_create_user_by_cookie(self)
        user_email = user.get_attr('email') if user else ""
        user_found = True if hasattr(user, 'fb_access_token') else False
        
        app = None
        referrer_link = None

        client = ClientShopify.all().filter('id =', rq_vars['store_id']).get()

        # If they give a bogus app id, show the landing page app!
        logging.info(client)
        if client == None:
            template_values = {
                'NAME' : NAME,
                
                'text': "",
                'willt_url' : URL,
                'willt_code': "",
                'app_uuid' : "",
                'target_url' : URL,
                
                'skip_to' : 'step2',
                'user' : user,
                'user_email' : user_email
            }
        else:
            app = ReferralShopify.all().filter('client =', client).get()

            # Make a Onew Link
            link = create_link(app.target_url, app, origin_domain, user)
            logging.info("link created is %s" % link.willt_url_code)

            # Fetch the Shopify Order
            order = get_shopify_order_by_token( rq_vars['order_token'] )

            # Create the share text
            if app.target_url in app.share_text:
                share_text = app.share_text.replace( app.target_url, link.get_willt_url() )
            else:
                share_text = app.share_text + " " + link.get_willt_url()
            
            template_values = {
                'URL' : URL,
                'NAME' : NAME,
                
                'app' : app,
                'app_uuid' : app.uuid,
                'text': share_text,
                'willt_url' : link.get_willt_url(),
                'willt_code': link.willt_url_code,
                'order_id': order.order_id if order else "",
                
                'user': user,
                'FACEBOOK_APP_ID': FACEBOOK_APP_ID,
                'user_email': user_email,
                'user_found': str(user_found).lower()
            }

            # Determine if they were referred
            referrer_cookie = self.request.cookies.get(app.uuid, False)
            referrer_link   = get_link_by_willt_code( referrer_cookie )
            
            if referrer_link:
                template_values['profile_pic']   = referrer_link.user.get_attr( 'pic' )
                template_values['referrer_name'] = referrer_link.user.get_attr( 'full_name' )
                template_values['show_gift']     = True
        
        if self.request.url.startswith('http://localhost'):
            template_values['BASE_URL'] = self.request.url[0:21]
        else:
            template_values['BASE_URL'] = URL
        
        # What plugin are we loading?
        path = ''
        if 'referral' in input_path:
            path = 'referral_plugin.html'

            # TODO (Barbara): Pull this out of here!!
            if referrer_link:
                add_referree_gift_to_shopify_order( order.order_id )

        elif 'bar' in input_path:
            self.response.headers['Content-Type'] = 'javascript'
            path = 'referral_top_bar.js'

        # Finally, render the plugin!
        path = os.path.join('apps/referral/templates/', path)
        self.response.out.write(template.render(path, template_values))
        return

