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

class LoadButtonsScript(webapp.RequestHandler):
    """When requested serves a plugin that will contain various functionality
       for sharing information about a purchase just made by one of our clients"""
    def get(self, input_path):
        """
        {{ URL }}/b/shopify/load/buttons.js?app_uuid={{app.uuid}}&willt_code={{willt_code}}');
        """
        template_values = {}
        app    = ButtonsShopify.get(self.request.get('app_uuid'))
        user   = get_or_create_user_by_cookie( self, app )

        template_values = {
            'app'            : app,
            'domain'         : app.client.domain if hasattr(app.client, 'domain') else app.client.url,
            'URL'            : URL,
        }
        
        # Finally, render it
        path = os.path.join('apps/buttons/templates/', input_path)
        self.response.headers.add_header('P3P', P3P_HEADER)
        
        if input_path.find('.js') != -1:
            # If the 'buttons.js" script is loaded, store a ScriptLoadAction
            ScriptLoadAction.create( user, app, get_target_url(self.request.headers.get('REFERER')))

            self.response.headers['Content-Type'] = 'javascript'
        
        self.response.out.write(template.render(path, template_values))
        return

