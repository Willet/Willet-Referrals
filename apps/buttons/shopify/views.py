#!/usr/bin/env python

import os
import logging
from django.utils import simplejson as json

from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from urlparse                   import urlparse

from apps.buttons.shopify.models import * 
from apps.app.models    import App
from apps.app.models    import get_app_by_id
from apps.user.models   import get_or_create_user_by_cookie
from apps.client.shopify.models import ShopifyClient
from apps.link.models   import create_link
from apps.link.models   import get_link_by_url
from apps.link.models   import get_link_by_willt_code

from util.consts        import *
from util.helpers       import get_request_variables
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
        client = ShopifyClient.get_by_url( shop )
        
        # Fetch or create the app
        app    = get_or_create_buttons_shopify_app(client, token)
        
        # Render the page
        template_values = {
            'app'        : app,
            'shop_owner' : client.merchant.get_attr('full_name') 
        }

        self.response.out.write(self.render_page('welcome.html', template_values)) 

class LoadButtonsIframe(webapp.RequestHandler):
    """When requested serves a plugin that will contain various functionality
       for sharing information about a purchase just made by one of our clients"""
    def get(self, input_path):
        """
        {{ URL }}/b/shopify/load/iframe.html?app_uuid={{app.uuid}}&willt_code={{willt_code}}');
        """
        template_values = {}
        user = get_or_create_user_by_cookie( self )
    
        # TODO: put this as a helper fcn.
        # Build a url for this page.
        try:
            page_url = urlparse(self.request.headers.get('REFERER'))
            target   = "%s://%s%s" % (page_url.scheme, page_url.netloc, page_url.path)
            fragment = page_url.fragment
            if fragment != '':
                parts = fragment.split('=')
                if len(parts) > 1:
                    # code a willt code!
                    willet_code = parts[1]
        except Exception, e:
            logging.error('error parsing referer %s: %s' % (
                    self.request.headers.get('referer'),
                    e
                ),
                exc_info=True
            )

        # set the stylesheet we are going to use
        style = self.request.get('style')
        if style == '':
            style = 'style'

        # Fetch the App
        app = get_app_by_id( self.request.get( 'app_uuid' ) )

        # Get the link
        willt_code = self.request.get('willt_code')
        if willt_code != "":
            link = get_link_by_willt_code( willt_code )

        template_values = {
            'willt_code'     : link.willt_url_code,
            'want_text'      : 'I want this!',
            'FACEBOOK_APP_ID': BUTTONS_FACEBOOK_APP_ID,
            'style'          : style,
            'user_found'     : True if hasattr(user, 'fb_access_token') else False,
        }
        
        # Finally, render the iframe
        path = os.path.join('apps/buttons/templates/', input_path)
        self.response.headers['Content-Type'] = 'text/html'
        self.response.out.write(template.render(path, template_values))
        return
