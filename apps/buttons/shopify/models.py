#!/usr/bin/env python

# Buttons model
# Extends from "App"

__author__ = "Willet, Inc."
__copyright__ = "Copyright 2011, Willet, Inc"

import hashlib
import logging
from datetime import timedelta, datetime
from urllib import urlencode

from django.utils import simplejson as json
from google.appengine.ext import db

from apps.app.shopify.models import AppShopify
from apps.buttons.models import Buttons
from apps.email.models import Email
from apps.link.models import Link

from util.consts import *
from util.helpers import generate_uuid
from util.shopify_helpers import get_shopify_url
from util.errors          import ShopifyBillingError

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

    def _validate_self(self):
        return True

    @staticmethod
    def get_by_uuid( uuid ):
        return ButtonsShopify.all().filter( 'uuid =', uuid ).get()

    def get_price(self):
        result = self._call_Shopify_API("GET", "shop.json?fields=created_at")

        now          = datetime.utcnow()
        shop_created = self._Shopify_str_to_datetime(result["shop"]["created_at"])
        start_date   = max(shop_created, now - timedelta(days=365))
        months       = ((now - start_date).days) / 30.0

        query_params = {
            "created_at_min": start_date.strftime("%Y-%m-%d %H:%M"),
            "updated_at_max": now.strftime("%Y-%m-%d %H:%M")
        }

        urlencoded_params = "?" + urlencode(query_params)

        result = self._call_Shopify_API("GET", "orders/count.json%s" % urlencoded_params)
        orders = int(result["count"])
        monthly_orders = orders / months if months else orders

        # PRICING CHART
        if monthly_orders < 10:
            price = 0.99 #non-profit
        elif monthly_orders < 20:
            price = 2.99 #basic
        elif monthly_orders < 50:
            price = 5.99 #professional
        elif monthly_orders < 100:
            price = 9.99 #business
        elif monthly_orders < 200:
            price = 17.99 #unlimited
        else:
            price = 19.99 #enterprise

        self.recurring_billing_price = unicode(price)
        self.put()
        return price

    def do_install(self):
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
        Email.welcomeClient("ShopConnection", 
                             self.client.email, 
                             self.client.merchant.get_full_name(), 
                             self.client.name)
        
        # Email DevTeam
        Email.emailDevTeam(
            'ButtonsShopify Install: %s %s %s' % (
                self.uuid,
                self.client.name,
                self.client.url
            )
        )

        # Start sending email updates
        if app_name in SHOPIFY_APPS and 'mailchimp_list_id' in SHOPIFY_APPS[app_name]:
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

        # Email DevTeam
        Email.emailDevTeam(
            'ButtonsShopify Upgrade: %s %s %s' % (
                self.uuid,
                self.client.name,
                self.client.url
            )
        )

    # Constructors ------------------------------------------------------------------------------
    @classmethod
    def create_app(cls, client, app_token):
        """ Constructor """
        uuid = generate_uuid(16)
        app = cls(key_name=uuid,
                  uuid=uuid,
                  client=client,
                  store_name=client.name, # Store name
                  store_url=client.url,  # Store url
                  store_id=client.id,   # Store id
                  store_token=app_token,
                  button_selector="_willet_buttons_app") 
        app.put()

        app.do_install()
            
        return app

    # 'Retreive or Construct'ers -----------------------------------------------------------------
    @classmethod
    def get_or_create_app(cls, client, token):
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
                    app.client = client
                    app.old_client = None
                    app.put()
                    
                    app.do_install()
                except:
                    logging.error('encountered error with reinstall', exc_info=True)
        return app

# TODO delete these deprecated functions after April 18, 2012 (1 month warning)
def create_shopify_buttons_app(client, app_token):
    raise DeprecationWarning('Replaced by ButtonShopify.create_app')

def get_or_create_buttons_shopify_app(client, token):
    raise DeprecationWarning('Replaced by ButtonShopify.get_or_create_app')
    ButtonShopify.get_or_create_app(client, token)

def get_shopify_buttons_by_url(store_url):
    raise DeprecationWarning('Replaced by ButtonShopify.get_by_url')
    ButtonShopify.get_by_url(store_url)

