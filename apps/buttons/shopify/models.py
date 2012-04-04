#!/usr/bin/env python

# Buttons model
# Extends from "App"

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc"

import sys
import hashlib
import logging
import datetime

from django.utils         import simplejson as json
from google.appengine.ext import db

from apps.app.shopify.models import AppShopify
from apps.buttons.models  import Buttons
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


class ButtonsShopify(Buttons, AppShopify):
    billing_enabled = db.BooleanProperty(indexed= False, default= False)

    def __init__(self, *args, **kwargs):
        """ Initialize this model """
        super(ButtonsShopify, self).__init__(*args, **kwargs)

    @staticmethod
    def get_by_uuid( uuid ):
        return ButtonsShopify.all().filter( 'uuid =', uuid ).get()

    def get_price(self):
        result = self._call_Shopify_API("GET", "orders/count.json")
        count = result["count"]

        # Method 1: The long 'if'
        def method1(count):
            if 0 <= count < 10:
                return 0.99 #non-profit
            elif 10 <= count < 100:
                return 2.99 #basic
            elif 100 <= count < 1000:
                return 5.99 #professional
            elif 1000 <= count < 10000:
                return 9.99 #business
            elif 10000 <= count < 100000:
                return 17.99 #unlimited
            elif 100000 <= count:
                return 19.99 #enterprise
            else:
                pass #TODO: Error

        # Method 2a: The Tuple-Dict Two-Step
        def method2a(count):
            # Apparently, python can use tuples as keys; Awesome!
            plans = {
                (0, 10)             : 0.99,     #"non-profit"
                (10, 100)           : 2.99,     #"basic"
                (100, 1000)         : 5.99,     #"professional"
                (1000, 10000)       : 9.99,     #"business"
                (10000, 100000)     : 17.99,    #"unlimited"
                (100000, sys.maxint): 19.99     #"enterprise"
            }

            keys = filter(lambda x: x[0] <= count < x[1], plans)
            if len(keys) is 1 and plans.get(keys[0]):
                return plans.get(keys[0])
            else:
                pass # TODO error! We messed up our ranges, or the key wasn't found!

        # Method 2b: The Tuple-Dict one step
        def method2b(count):
            # Apparently, python can use tuples as keys; Awesome!
            plans = {
                (0, 10)             : 0.99,     #"non-profit"
                (10, 100)           : 2.99,     #"basic"
                (100, 1000)         : 5.99,     #"professional"
                (1000, 10000)       : 9.99,     #"business"
                (10000, 100000)     : 17.99,    #"unlimited"
                (100000, sys.maxint): 19.99     #"enterprise"
            }

            plan_prices = [value for key, value in plans.iteritems() if key[0] <= count < key[1]]
            if len(plan_prices) is 1:
                return plan_prices[0]
            else:
                pass #TODO: Error!

        return method1(count)

    def do_install( self ):
        """ Install Buttons scripts and webhooks for this store """
        app_name = self.__class__.__name__

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
        self.queue_webhooks(product_hooks_too=False)
        self.queue_script_tags(script_tags=tags)

        self.install_queued()

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

        # Start sending email updates
        if 'mailchimp_list_id' in SHOPIFY_APPS[app_name]:
            self.client.subscribe_to_mailing_list(
                list_name=app_name,
                list_id=SHOPIFY_APPS[app_name]['mailchimp_list_id']
            )
        
        return

    def do_upgrade(self):
        """ Remove button scripts and add the paid version """
        self.uninstall_script_tags();
        self.queue_script_tags(script_tags=[{
            "script_tag": {
                "src": "%s/b/shopify/load/smart-buttons.js?app_uuid=%s" % (
                    URL,
                    self.uuid
                ),
                "event": "onload"
            }
        }])
        self.install_queued()

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

    # Constructors ------------------------------------------------------------------------------
    @classmethod
    def create_app(cls, client, app_token):
        """ Constructor """
        uuid = generate_uuid( 16 )
        app = cls(key_name=uuid,
                  uuid=uuid,
                  client=client,
                  store_name=client.name, # Store name
                  store_url=client.url,  # Store url
                  store_id=client.id,   # Store id
                  store_token=app_token,
                  button_selector="_willet_buttons_app" ) 
        app.put()

        app.do_install()
            
        return app

    # 'Retreive or Construct'ers -----------------------------------------------------------------
    @classmethod
    def get_or_create_app(cls, client, token ):
        """ Try to retrieve the app.  If no app, create one """
        app = cls.get_by_url(client.url)
        
        if app is None:
            app = cls.create_app(client, token)
        
        elif token != None and token != '':
            if app.store_token != token:
                # TOKEN mis match, this might be a re-install
                logging.warn(
                    'We are going to reinstall this app because the stored\
                     token does not match the request token\n%s vs %s' % (
                        app.store_token,
                        token
                    )
                ) 
                try:
                    app.store_token = token
                    app.client      = client
                    app.old_client  = None
                    app.put()
                    
                    app.do_install()
                except:
                    logging.error('encountered error with reinstall', exc_info=True)
        return app

# TODO delete these deprecated functions after April 18, 2012 (1 month warning)
def create_shopify_buttons_app(client, app_token):
    raise DeprecationWarning('Replaced by ButtonShopify.create_app')
    ButtonShopify.create_app(client, app_token)

def get_or_create_buttons_shopify_app(client, token):
    raise DeprecationWarning('Replaced by ButtonShopify.get_or_create_app')
    ButtonShopify.get_or_create_app(client, token)

def get_shopify_buttons_by_url( store_url ):
    raise DeprecationWarning('Replaced by ButtonShopify.get_by_url')
    ButtonShopify.get_by_url(store_url)

