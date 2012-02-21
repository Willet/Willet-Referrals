#!/usr/bin/env python

import logging

from google.appengine.ext           import webapp
from google.appengine.ext.webapp    import template
from urlparse                       import urlparse

from apps.buttons.shopify.models    import * 
from apps.client.shopify.models     import ClientShopify
from util.consts                    import *
from util.urihandler                import URIHandler

class ButtonsShopifyBeta(URIHandler):
    def get(self):
        template_values = {
            "SHOPIFY_API_KEY": SHOPIFY_APPS['ButtonsShopify']['api_key']
        }
        
        self.response.out.write(self.render_page('beta.html', template_values))

class ButtonsShopifyBillingCallback(URIHandler):
    def get(self):
        app = App.get_by_uuid( self.request.get('app_uuid') )
        app.billing_enabled = True

        url      = '%s/admin/recurring_application_charges.json' % app.store_url
        username = app.settings['api_key'] 
        password = hashlib.md5(app.settings['api_secret'] + app.store_token).hexdigest()
        header   = {'content-type':'application/json'}
        h        = httplib2.Http()
        
        # Auth the http lib
        h.add_credentials(username, password)
        
        # First fetch webhooks that already exist
        resp, content = h.request( url, "GET", headers = header )
        data = json.loads( content ) # there will be a list.

        id = data['recurring_application_charges']['id']

        url      = '%s/admin/recurring_application_charges/#{id}/activate.json' % (app.store_url, id)
        username = app.settings['api_key'] 
        password = hashlib.md5(app.settings['api_secret'] + app.store_token).hexdigest()
        header   = {'content-type':'application/json'}
        h        = httplib2.Http()
        
        # Auth the http lib
        h.add_credentials(username, password)
        
        # First fetch webhooks that already exist
        resp, content = h.request( url, "GET", headers = header )
        data = json.loads( content ) 


        self.response.out.write(self.render_page('beta.html', template_values))

class ButtonsShopifyWelcome(URIHandler):
    def get( self ):
        # TODO: put this somewhere smarter
        shop   = self.request.get( 'shop' )
        token  = self.request.get( 't' )

        # Fetch the client
        client = ClientShopify.get_by_url( shop )
    
        # Fetch or create the app
        app, confirm_url  = get_or_create_buttons_shopify_app(client, token=token)
        
        # If we're setting up billing
        if confirm_url:
            self.redirect( confirm_url )
            return

        # Render the page
        template_values = {
            'app'        : app,
            'shop_owner' : client.merchant.get_full_name(),
            'shop_name'  : client.name
        }

        self.response.out.write(self.render_page('welcome.html', template_values)) 

