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
from apps.wosib.shopify.models import WOSIBShopify

from util.shopify_helpers import get_shopify_url
from util.helpers             import *
from util.urihandler          import URIHandler
from util.consts              import *

class WOSIBShopifyWelcome (URIHandler):
    # class name is locked by a class/func called ShopifyRedirect
    def get(self):
        logging.info('trying to create app')
        try:
            client = self.get_client() # May be None if not authenticated
            logging.debug ('client is %s' % client)        
            token = self.request.get('t') # token
            app = WOSIBShopify.get_or_create(client, token=token)

            client_email = None
            shop_owner   = 'Shopify Merchant'
            shop_name    = 'Your Shopify Store'
            if client is not None and client.merchant is not None:
                client_email = client.email
                shop_owner   = client.merchant.get_attr('full_name')
                shop_name    = client.name

            template_values = {
                'app': app,
                'URL' : URL,
                'shop_name' : shop_name,
                'shop_owner': shop_owner,
                'client_email': client_email,
                'client_uuid' : client.uuid,
            }

            self.response.out.write( self.render_page( 'welcome.html', template_values)) 
        except:
            logging.error('wtf: (apps/wosib/shopify)', exc_info=True)

class WOSIBShowBetaPage (URIHandler):
    def get(self):
        logging.info(SHOPIFY_APPS)
        logging.info(SHOPIFY_APPS['WOSIBShopify'] )
        template_values = { 'SHOPIFY_API_KEY' : SHOPIFY_APPS['WOSIBShopify']['api_key'] }
        
        self.response.out.write(self.render_page('beta.html', template_values))

class SIBTShopifyEditStyle (URIHandler):
    def get(self):
        # later
        pass

class WOSIBShowFinishedPage (URIHandler):
    def get(self):
        # what does it do?
        pass

class WOSIBShopifyServeScript (webapp.RequestHandler):
    # chucks out a javascript that helps detect events and show wizards.
    def get(self):
        shop_url = app = None
        template_values = {}

        if self.request.get('store_url'):
            shop_url    = get_shopify_url(self.request.get('store_url'))
            app         = WOSIBShopify.get_by_store_url(shop_url)

        if self.request.get('page_url'):
            target = get_target_url(self.request.get('page_url'))
        else:
            target = get_target_url(self.request.headers.get('REFERER'))

        user = get_or_create_user_by_cookie( self, app )

        template_values = {
            'evnt' : '', #TODO
            'app' : app,
            'URL': URL,
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
        self.get() # because post.
