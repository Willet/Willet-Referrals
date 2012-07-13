#!/usr/bin/python

# client models
# data models for our clients and associated methods

__author__ = "Willet, Inc."
__copyright__ = "Copyright 2011, Willet, Inc"

import hashlib
import logging
import math

from django.utils import simplejson as json
from google.appengine.api import taskqueue
from google.appengine.ext import db

from apps.client.models import Client
from apps.order.shopify.models import OrderShopify
from apps.product.shopify.models import ProductShopify
from apps.user.models import User

from util import httplib2
from util.consts import SHOPIFY_APPS
from util.helpers import generate_uuid
from util.helpers import url as build_url
from util.shopify_helpers import get_shopify_url


class ClientShopify(Client):
    """A Client of a Shopify website.

    ClientShopify models are meant for Shopify shops only - use Client to
    store information about stores without a specific platform.
    """
    token = db.StringProperty(default='')
    id = db.StringProperty(indexed = True)

    def __init__(self, *args, **kwargs):
        """ Initialize this obj """
        super(ClientShopify, self).__init__(*args, **kwargs)

    def _validate_self(self):
        self.url = get_shopify_url(self.url)

    # Constructor
    @staticmethod
    def create(url_, token, request_handler, app_type):
        """ Create a Shopify Store as a Client"""

        url_ = get_shopify_url(url_)

        # Query the Shopify API to learn more about this store
        data = get_store_info(url_, token, app_type)

        # Make the Merchant
        # Note: App is attached later to the UserCreation action
        merchant = User.get_or_create_by_email(data['email'], request_handler, None)
        logging.info('MERCHANT UUID %s' % merchant.uuid)
        logging.info('MERCHANT Key %s' % merchant.key())

        # Now, make the store
        uuid = generate_uuid(16)
        domain = get_shopify_url(data['domain'])
        if domain == '':
            domain = url_

        store = ClientShopify(key_name=uuid,
                              uuid=uuid,
                              email=data['email'],
                              passphrase='',
                              name=data['name'],
                              url=url_,
                              domain=domain,
                              token=token,
                              id=unicode(data['id']),
                              merchant=merchant)

        store.put()

        # Update the merchant with data from Shopify
        merchant.update(full_name=data['shop_owner'],
                        address1=data['address1'],
                        address2=getattr(data, 'address2', ''),
                        city=data['city'],
                        province=data['province'],
                        country=data['country'],
                        postal_code= data['zip'],
                        phone=data['phone'],
                        client=store)

        logging.info("created store %r" % store)

        # Query the Shopify API to dl all Products
        taskqueue.add(url=build_url('FetchShopifyProducts'),
                      params={'client_uuid': uuid,
                              'app_type': app_type})

        return store

    @staticmethod
    def get_by_url(store_url):
        store_url = get_shopify_url(store_url)
        #logging.warning ("looking for client with url: %s" % store_url)
        store = ClientShopify.all().filter('url =', store_url).get()
        return store

    @staticmethod
    def get_by_id(id):
        return ClientShopify.all().filter('id =', id).get()

    @staticmethod
    def get_or_create(store_url, store_token='',
                      request_handler=None, app_type=""):
        store = ClientShopify.get_by_url(store_url)

        if not store:
            store = ClientShopify.create(store_url,
                                         store_token,
                                         request_handler,
                                         app_type)
        return store

    def get_products(self, app_type):
        """ Fetch images for all the products in this store """

        # Construct the API URL
        url = '%s/admin/products.json' % (self.url)
        logging.info ("url = %s" % url)

        # Fix inputs (legacy)
        if app_type == "sibt":
            app_type = 'SIBTShopify'
        elif app_type == 'buttons':
            app_type = "ButtonsShopify"

        # Grab Shopify API settings
        settings = SHOPIFY_APPS[app_type]

        # Constuct the API URL
        username = settings['api_key']
        password = hashlib.md5(settings['api_secret'] + self.token).hexdigest()
        header = {'content-type':'application/json'}
        h = httplib2.Http()

        # Auth the http lib
        h.add_credentials(username, password)

        logging.info("Querying %s" % url)
        resp, content = h.request(url, "GET", headers=header)

        details = json.loads(content)
        products = None
        try:
            logging.debug ("got json: %r" % details)
            assert ('products' in details)
            products = details['products']
        except:
            # details will not have ['products'] if response is incorrect.
            raise RemoteError (resp.status, resp.reason, products)

        for p in products:
            ProductShopify.create_from_json(self, p)

    @property
    def lead_score(self):
        """Returns a float (1 ~ 10) denoting the "lead" (whatever that is)
        of the store.

        Currently supports Shopify only. To expand to other services, move
        this function to the parent class.
        """
        base_score = 0
        orders = []

        try:
            # try to get the first Shopify app for this client for a token
            app = [a for a in self.apps if hasattr(a, '_call_Shopify_API')][0]
            if app:
                orders = OrderShopify.fetch(app=app, save=False)
                logging.debug('got app; orders = %r' % orders)
        except AttributeError, err:
            logging.error(err, exc_info=True)

        orders = orders or self.orders  # prioritise fresh orders
        if orders:
            for order in orders:
                logging.debug('got order %r' % order)
                base_score += order.subtotal_price

            # give higher score to retailers who sell TONS of cheap stuff
            # (i.e. high traffic)

            # Workaround until we find out why orders is sometimes a Query obj.
            if hasattr(orders, "len"):
                base_score = base_score * len(orders)


        logging.debug('base_score = %r' % base_score)
        if base_score:  # i.e. !0
            return round(max(1, min(10, math.log(base_score, 6))),2)  # 1~10
        else:
            return 1  # minimum is 1


def get_store_info(store_url, store_token, app_type):
    """Shopify API Calls"""

    # Fix inputs (legacy)
    if app_type == "sibt":
        app_type = 'SIBTShopify'
    elif app_type == "buttons":
        app_type = 'ButtonsShopify'

    # Grab Shopify API settings
    settings = SHOPIFY_APPS[app_type]

    # Constuct the API URL
    url = '%s/admin/shop.json' % (store_url)
    username = settings['api_key']
    password = hashlib.md5(settings['api_secret'] + store_token).hexdigest()
    header = {'content-type':'application/json'}
    h = httplib2.Http()

    # Auth the http lib
    h.add_credentials(username, password)

    logging.info("Querying %s" % url)
    resp, content = h.request(url, "GET", headers = header)

    details = json.loads(content)
    logging.info(details)
    shop = details['shop']
    logging.info('shop: %s' % (shop))

    return shop