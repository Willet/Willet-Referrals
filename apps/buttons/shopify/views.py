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
from apps.client.models import ClientShopify
from apps.client.models import get_shopify_client_by_url
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
        client = self.get_client() # May be None
       
        # TODO: put this somewhere smarter
        app_token = self.request.get( 't' )
        app = get_or_create_buttons_shopify_app(client, app_token)
        
        shop_owner = 'a Shopify store'
        if client:
            shop_owner = client.merchant.get_attr('full_name')

        template_values = {
            'app'        : app,
            'shop_owner' : shop_owner 
        }

        self.response.out.write(self.render_page('welcome.html', template_values)) 

class ButtonsShopifyJS(webapp.RequestHandler):
    """When requested serves a plugin that will contain various functionality
       for sharing information about a purchase just made by one of our clients"""
    def get(self, input_path):
        template_values = {}
        rq_vars = get_request_variables(['store_url'], self)

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

        # Make a new Link
        willt_code = self.request.get('willt_code')
        if willt_code != "":
            link = get_link_by_willt_code( willt_code )
        else:
            logging.info("Making a link for %s" % target)
            link = get_link_by_url(target)
            if link == None:
                # link does not exist yet
                link = create_link(target, app, self.request.url, user)

        template_values = {
            'app'            : app,
            'willt_url'      : link.get_willt_url(),
            'willt_code'     : link.willt_url_code,
            'want_text'      : 'I want this!',
            'URL'            : URL, 
            'FACEBOOK_APP_ID': BUTTONS_FACEBOOK_APP_ID,
            'style'          : style,
            'user_found'     : True if hasattr(user, 'fb_access_token') else False,
        }
        
        # Finally, render the plugin!
        path = os.path.join('apps/buttons/templates/', input_path)
        
        if input_path.find('.js') != -1:
            self.response.headers['Content-Type'] = 'javascript'
        else:
            # If the 'Want' button is shown, store a PageView
            PageView.create( user, app, target )

            self.response.headers['Content-Type'] = 'text/html'
        self.response.out.write(template.render(path, template_values))
        return

