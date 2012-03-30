#!/usr/bin/env python

# Buttons model
# Extends from "App"

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc"

import hashlib
import logging
import datetime

from django.utils         import simplejson as json
from google.appengine.ext import db

from apps.app.shopify.models import AppShopify
from apps.buttons.models  import Buttons, ClientsButtons, ButtonsFBActions 
from apps.client.shopify.models   import ClientShopify
from apps.email.models    import Email
from apps.link.models     import Link

from util.consts          import *
from util.helpers         import generate_uuid
from util.shopify_helpers import get_shopify_url

NUM_VOTE_SHARDS = 15

# basic layout:
#   client installs button app
#       client adds buttons
#       each button has a buttonFBAction type

# ------------------------------------------------------------------------------
# Button Class Definition --------------------------------------------------------
# ------------------------------------------------------------------------------
class ButtonsShopify(Buttons, AppShopify):
    billing_enabled = db.BooleanProperty(indexed= False, default= False)

    def __init__(self, *args, **kwargs):
        """ Initialize this model """
        super(ButtonsShopify, self).__init__(*args, **kwargs)

    @staticmethod
    def get_by_uuid( uuid ):
        return ButtonsShopify.all().filter( 'uuid =', uuid ).get()

    def do_install( self ):
        """ Install Buttons scripts and webhooks for this store """
        # Define our script tag 
        tags = [{
            "script_tag": {
                "src": "%s/b/shopify/load/buttons.js?app_uuid=%s" % (
                    URL,
                    self.uuid
                ),
                "event": "onload"
            }
        }]

        # Install yourself in the Shopify store
        self.install_webhooks()
        self.install_script_tags(script_tags=tags)

        # Fire off "personal" email from Fraser
        Email.welcomeClient( "ShopConnection", 
                             self.client.email, 
                             self.client.merchant.get_full_name(), 
                             self.client.name )
        
        # Email DevTeam
        Email.emailDevTeam(
            'ButtonsShopify Install: %s %s %s' % (
                self.uuid,
                self.client.name,
                self.client.url
            )
        )

        return True

    def do_upgrade(self):
        """ Remove button scripts and add the paid version """
        self.uninstall_script_tags();
        self.install_script_tags(script_tags=[{
            "script_tag": {
                "src": "%s/b/shopify/load/smart-buttons.js?app_uuid=%s" % (
                    URL,
                    self.uuid
                ),
                "event": "onload"
            }
        }])

        # Fire off "personal" email from Fraser
        #Email.welcomeClient( "ShopConnection", 
        #                     self.client.email, 
        #                     self.client.merchant.get_full_name(), 
        #                     self.client.name )

        # Email DevTeam
        #Email.emailDevTeam(
        #    'ButtonsShopify Upgrade: %s %s %s' % (
        #        self.uuid,
        #        self.client.name,
        #        self.client.url
        #    )
        #)


# Constructor ------------------------------------------------------------------
def create_shopify_buttons_app(client, app_token):

    uuid = generate_uuid( 16 )
    app = ButtonsShopify( key_name          = uuid,
                          uuid              = uuid,
                          client            = client,
                          store_name        = client.name, # Store name
                          store_url         = client.url,  # Store url
                          store_id          = client.id,   # Store id
                          store_token       = app_token,
                          button_selector   = "_willet_buttons_app",
                          recurring_billing_status = 'none' )
    
    # Define recurring billing settings
    billing_settings = {
        "price":        0.99,
        "name":         "ShopConnection",
        "return_url":   "%s/b/shopify/billing_callback?app_uuid=%s" % (URL, self.uuid),
        "test":         "true", # Set to false when live
        "trial_days":   0
    }
    
    confirm_url = app.setup_recurring_billing(billing_settings)
    
    app.put()

    return app, confirm_url

# Accessors --------------------------------------------------------------------
def get_or_create_buttons_shopify_app( client, token ):
    confirm_url = None
    app = get_shopify_buttons_by_url( client.url )
    
    if app is None:
        app, confirm_url = create_shopify_buttons_app(client, token)
    
    elif token != None and token != '':
        if app.store_token != token:
            # TOKEN mis match, this might be a re-install
            logging.warn(
                'We are going to reinstall this app because the stored token does not match the request token\n%s vs %s' % (
                    app.store_token,
                    token
                )
            ) 
            try:
                app.store_token = token
                app.client      = client
                app.old_client  = None
                app.put()
                
                confirm_url = app.do_install()
            except:
                logging.error('encountered error with reinstall', exc_info=True)
    return app, confirm_url

def get_shopify_buttons_by_url( store_url ):
    """ Fetch a Shopify obj from the DB via the store's url"""
    store_url = get_shopify_url( store_url )

    logging.info("Shopify: Looking for %s" % store_url)
    return ButtonsShopify.all().filter( 'store_url =', store_url ).get()

