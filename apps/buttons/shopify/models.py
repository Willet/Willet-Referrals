#!/usr/bin/env python

# Buttons model
# Extends from "App"
from itertools import groupby

__author__ = "Willet, Inc."
__copyright__ = "Copyright 2011, Willet, Inc"

import hashlib
import logging
from datetime import date, datetime, timedelta
from time import time
from urllib import urlencode

from django.utils import simplejson as json
from google.appengine.ext import db

from apps.app.shopify.models import AppShopify
from apps.buttons.models import Buttons
from apps.email.models import Email
from apps.link.models import Link

from util.model import Model, ObjectListProperty
from util.consts import *
from util.helpers import generate_uuid
from util.shopify_helpers import get_shopify_url
from util.errors          import ShopifyBillingError, ShopifyAPIError

NUM_VOTE_SHARDS = 15

# basic layout:
#   client installs button app
#       client adds buttons
#       each button has a buttonFBAction type


class ButtonsShopify(Buttons, AppShopify):
    billing_enabled = db.BooleanProperty(indexed=True, default= False)

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

    def update_prefs(self, preferences):
        """Update preferences for the application."""
        if self.billing_enabled:
            json_preferences = json.dumps(preferences)

            script = """
                <script type="text/javascript">
                    (function(){
                        /*----*/
                        window._willet_shopconnection_preferences = %s;
                        /*----*/
                    })
                </script>
            """ % json_preferences

            self.queue_assets(assets=[{
                'asset': {
                    'key': 'snippets/willet-shopconnection.liquid',
                    'value': script
                }
            }])
            self.install_queued()

    def get_prefs(self):
        """Get preferences, provided that they exist."""
        #need to get theme id first...
        result = self._call_Shopify_API("GET", "themes.json")

        theme_id = None
        for theme in result['themes']:
            if 'role' in theme and 'id' in theme:
                if theme['role'] == 'main':
                    theme_id = theme['id']
                    break

        query_params = urlencode({
            "asset[key]": "snippets/willet-shopconnection.liquid",
            "theme_id": theme_id
        })

        prefs = {
            'button_count'  : False,
            'button_spacing': -1,
            'button_padding': -1
        }
        try:
            result = self._call_Shopify_API("GET",
                                   "themes/%s/assets.json?%s" %
                                   (theme_id, query_params))

            if result["asset"] and result["asset"]["value"]:
                value           = result["asset"]["value"]
                _, var_value, _ = value.split("/*----*/")
                _, json_str     = var_value.split("=")
                prefs           = json.loads(json_str.strip().strip(";"))
        except ShopifyAPIError:
            pass  # No asset found; probably doesn't exist yet
        except ValueError:
            pass  # TODO: Problem parsing the JSON

        logging.info(prefs)
        return prefs

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
        created = False
        app = cls.get_by_url(client.url)
        
        if app is None:
            app = cls.create_app(client, token)
            created = True
        
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
                    created = True
                except:
                    logging.error('encountered error with reinstall', exc_info=True)
        return app, created

class SharedItem():
    """An object that contains information about a share"""
    def __init__(self, name, network, url, img_url=None, created=None):
        """Constructor for SharedItems

            name   : Name of the item
            network: Network that the item was shared on
            url    : URL where item is located, if available
            img_url: URL of image for item, if available
        """
        # Should we also include a unique item ID? Can we obtain one?
        self.name    = name
        self.network = network
        self.url     = url
        self.img_url = img_url
        self.created = created if created else time()

class SharePeriod(Model):
    """Model that manages shares for an application over some period"""
    app_uuid = db.StringProperty(indexed=True)
    start    = db.DateProperty(indexed=True)
    end      = db.DateProperty(indexed=True)
    shares   = ObjectListProperty(SharedItem, indexed=False)

    def __init__(self, *args, **kwargs):
        """Initialize this model """
        self._memcache_key = kwargs['uuid'] if 'uuid' in kwargs else None
        super(SharePeriod, self).__init__(*args, **kwargs)

    def _validate_self(self):
        """Ensure that this object is in a valid state"""
        return (self.start < self.end)

    @classmethod
    def get_or_create(cls, app):
        """Gets or creates a new SharePeriod instance"""
        now = date.today()

        # Get the latest period for this app
        instance = cls.all()\
                    .filter('app_uuid =', app.uuid)\
                    .order('-end')\
                    .get()

        if instance is None or now > instance.end:
            # Go back to Monday
            # http://stackoverflow.com/questions/1622038/find-mondays-date-with-python
            start = now - timedelta(days=now.weekday())
            end   = start + timedelta(weeks=1)

            instance = cls(app_uuid=app.uuid, start=start, end=end)

        return instance

    def get_shares_grouped_by_network(self):
        items = self.shares
        sorted_items   = sorted(items, key=lambda v: v.network)
        group_by_network_iter = groupby(sorted_items, lambda v: v.network)

        items_by_network  = []
        for network_name, network in group_by_network_iter:
            network_count = len(list(network))
            percent = (100 * network_count) / len(self.shares)
            items_by_network.append({
                "network": network_name,
                "shares": network_count,
                "percent": percent
            })

        return items_by_network

    #Maybe Refactor to use sort_shares_by_network? common functionality?
    def get_shares_grouped_by_product(self):
        items = self.shares
        sorted_items   = sorted(items, key=lambda v: v.name)
        group_by_name_iter = groupby(sorted_items, lambda v: v.name)

        items_by_name  = []
        for product_name, product in group_by_name_iter:
            item = {}
            item["name"] = product_name
            product_shares = list(product) # evaluates the iterator
            total_shares = len(product_shares)
            item["total_shares"] = total_shares

            networks = []
            sorted_product_shares = sorted(product_shares,
                                           key=lambda v: v.network)
            group_by_network_iter = groupby(sorted_product_shares,
                                            lambda v: v.network)
            for network_name, network in group_by_network_iter:
                network_count = len(list(network))
                percent = (100 * network_count) / total_shares
                networks.append({
                    "network": network_name,
                    "shares": network_count,
                    "percent": percent
                })
            item["networks"] = sorted(networks, key=lambda v: v["shares"],
                                      reverse=True)
            items_by_name.append(item)
        return items_by_name


# TODO delete these deprecated functions after April 18, 2012 (1 month warning)
def create_shopify_buttons_app(client, app_token):
    raise DeprecationWarning('Replaced by ButtonShopify.create_app')

def get_or_create_buttons_shopify_app(client, token):
    raise DeprecationWarning('Replaced by ButtonShopify.get_or_create_app')
    ButtonShopify.get_or_create_app(client, token)[0]

def get_shopify_buttons_by_url(store_url):
    raise DeprecationWarning('Replaced by ButtonShopify.get_by_url')
    ButtonShopify.get_by_url(store_url)

