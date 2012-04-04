#!/usr/bin/env python

import logging

from google.appengine.ext           import webapp
from google.appengine.ext.webapp    import template
from urlparse                       import urlparse

from apps.buttons.shopify.models    import * 
from apps.client.shopify.models     import ClientShopify
from util.consts                    import *
from util.errors                    import ShopifyBillingError
from util.urihandler                import URIHandler

class ButtonsShopifyBeta(URIHandler):
    """ If an existing customer clicks through from Shopify """
    def get(self):
        template_values = {
            "SHOPIFY_API_KEY": SHOPIFY_APPS['ButtonsShopify']['api_key']
        }
        
        self.response.out.write(self.render_page('beta.html', template_values))

class ButtonsShopifyApproveBilling(URIHandler):
    """ Where a customer is directed after they accept an app install through Shopify 

    Gets billing confirmation_url from Shopify, then redirects user there
    """
    def get(self): 
        shop   = self.request.get('shop')
        token  = self.request.get('t')

        # Fetch the client
        client = ClientShopify.get_by_url( shop )
        
        # Fetch or create the app
        app, confirm_url  = get_or_create_buttons_shopify_app(client, token=token)

class ButtonsShopifyWelcome(URIHandler):
    def get( self ):
        # TODO: put this somewhere smarter
        shop   = self.request.get( 'shop' )
        token  = self.request.get( 't' )

        # Fetch the client
        client = ClientShopify.get_by_url( shop )
    
        # Fetch or create the app
        app    = ButtonsShopify.get_or_create_app(client, token=token)

        # Render the page
        template_values = {
            'app'          : app,
            'shop_owner'   : client.merchant.get_full_name(),
            'shop_name'    : client.name
            #'continue_url' : #####!!!!!##### # TODO: What is this for
        }

        self.response.out.write(self.render_page('welcome.html', template_values))

class SmartButtonsShopifyBillingCallback(URIHandler):
    """ When a customer confirms / denies billing, they are redirected here

    Activates billing with Shopify, then redirects customer to installation instructions
    """
    def get(self):
        app_uuid =self.request.get('app_uuid')
        app = ButtonsShopify.get_by_uuid(app_uuid)

        if not app:
            # TODO: Error! What is going on?!
            pass

        charge_id = int(self.request.get('charge_id'))

        if charge_id == app.recurring_billing_id:
            logging.info(self.request.arguments())

            # Good to go, activate!
            app.activate_recurring_billing({
                'return_url': self.request.url,
                'test': 'true'
            })
            app.billing_enabled = True

            app.put()

            app.do_upgrade();
        else:
            raise ShopifyBillingError('Charge id in request does not match expected charge id', app.recurring_billing_id)

        # Fetch the client
        client = ClientShopify.get_by_uuid(app_uuid)

        # Render the page
        template_values = {
            'app'        : app,
            'shop_owner' : client.merchant.get_full_name(),
            'shop_name'  : client.name
        }
        self.response.out.write(self.render_page('beta.html', template_values))

class SmartButtonsShopifyUpgrade(URIHandler):
    """ Starts the upgrade process """
    def get(self):
        shop_url = self.request.get("shop_url")

        existing_app = ButtonsShopify.get_by_url(shop_url)
        if existing_app is None:
            # TODO: Error, can't upgrade if not installed
            pass

        price = existing_app.get_price()

        # Start the billing process
        confirm_url = existing_app.setup_recurring_billing({
            "price":        price,
            "name":         "ShopConnection",
            "return_url":   "%s/sb/shopify/billing_callback?app_uuid=%s" % (URL, existing_app.uuid),
            "test":         "true" # Set to false when live; can't run 'false' when in development
            #"trial_days":   0
        })

        existing_app.put()

        if confirm_url:
            self.redirect(confirm_url)
            return
        else:
            # TODO: What happened?
            pass

class SmartButtonsShopifyWelcome(URIHandler):
    """ Shows the user basic installation instructions """
    def get(self):
        pass

class SmartButtonsShopifyBeta(URIHandler):
    """ If an existing customer clicks through from Shopify """
    def get(self):
        self.response.out.write(self.render_page('smart-beta.html', {}))
