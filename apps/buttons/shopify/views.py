#!/usr/bin/env python

import logging

from google.appengine.ext           import webapp
from google.appengine.ext.webapp    import template
from urlparse                       import urlparse

from apps.buttons.shopify.models    import * 
from apps.client.shopify.models     import ClientShopify
from apps.sibt.shopify.models       import * 
from apps.wosib.shopify.models      import * 
from util.consts                    import *
from util.urihandler                import URIHandler

class ButtonsShopifyBeta(URIHandler):
    def get(self):
        template_values = {
            "SHOPIFY_API_KEY": SHOPIFY_APPS['AppShopify']['api_key']
        }
        
        self.response.out.write(self.render_page('beta.html', template_values))

class ButtonsShopifyWelcome(URIHandler):
    def get( self ):
        # TODO: put this somewhere smarter
        shop   = self.request.get( 'shop' )
        token  = self.request.get( 't' )

        # Fetch the client
        client = ClientShopify.get_by_url( shop )
        
        if not client or not token:
            self.error (400) # bad request
            return
        
        # update client token (needed when reinstalling)
        if client.token != token:
            logging.debug ("token was %s; updating to %s." % (client.token if client else None, token))
            client.token = token
            client.put()
    
        # Fetch or create the app
        app = ButtonsShopify.get_or_create_app(client, token=token)
        try:
            app2 = SIBTShopify.get_or_create (client=client, token=token, email_client=False)
        except Exception, e:
            logging.error ('cannot bundle SIBT with buttons install: %s' % e)
        
        try:
            app3 = WOSIBShopify.get_or_create (client=client, token=token, email_client=False)
        except Exception, e:
            logging.error ('cannot bundle WOSIB with buttons install: %s' % e)
        
        # Render the page
        template_values = {
            'app'        : app,
            'shop_owner' : client.merchant.get_full_name(),
            'shop_name'  : client.name
        }

        self.response.out.write(self.render_page('welcome.html', template_values)) 

