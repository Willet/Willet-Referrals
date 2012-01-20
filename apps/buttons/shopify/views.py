#!/usr/bin/env python

import os
import logging
from django.utils import simplejson as json

from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from urlparse                   import urlparse

from apps.action.models import ScriptLoadAction
from apps.action.models import ButtonLoadAction
from apps.app.models    import App
from apps.app.models    import get_app_by_id
from apps.buttons.shopify.models import * 
from apps.client.shopify.models  import ClientShopify
from apps.link.models   import create_link
from apps.link.models import Link
from apps.link.models   import get_link_by_url
from apps.link.models   import get_link_by_willt_code
from apps.user.models   import get_or_create_user_by_cookie

from util.consts        import *
from util.helpers       import get_request_variables
from util.helpers       import get_target_url
from util.urihandler    import URIHandler

class ButtonsShopifyBeta(URIHandler):
    def get(self):
        template_values = {
            "SHOPIFY_API_KEY": SHOPIFY_APPS['ButtonsShopify']['api_key']
        }
        
        self.response.out.write(self.render_page('beta.html', template_values))

class ButtonsShopifyWelcome(URIHandler):
    def get( self ):
        # TODO: put this somewhere smarter
        shop   = self.request.get( 'shop' )
        token  = self.request.get( 't' )

        # Fetch the client
        client = ClientShopify.get_by_url( shop )
    
        # Fetch or create the app
        app    = get_or_create_buttons_shopify_app(client, token=token)
        
        # Render the page
        template_values = {
            'app'        : app,
            'shop_owner' : client.merchant.get_full_name(),
            'shop_name'  : client.name
        }

        self.response.out.write(self.render_page('welcome.html', template_values)) 

