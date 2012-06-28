#!/usr/bin/python

"""The OrderShopify model."""

__author__ = "Willet, Inc."
__copyright__ = "Copyright 2012, Willet, Inc"

import datetime
import logging

from urllib import urlencode

from google.appengine.ext import db

from apps.app.shopify.models import AppShopify
from apps.order.models import Order
from apps.user.models import User

from util.errors import ShopifyAPIError
from util.helpers import generate_uuid
from util.model import Model


class OrderShopify(Order):
    """A subclass of Order Model specific to Shopify.

    Stores information about a purchase / point of conversion.

    Orders in the datastore may or may not be attributed to us (i.e.
    you can't say order 123 is by the help of ReEngage just because we
    have it in our database.)
    """
    order_token = db.StringProperty(indexed=True)
    order_id = db.StringProperty(indexed=True)
    order_number = db.StringProperty(indexed=False)

    store_name = db.StringProperty(indexed=False)
    store_url = db.StringProperty(indexed=False, required=False, default=None)

    referring_site = db.StringProperty(indexed=False, required=False,
                                       default=None) # might be useful

    def __init__(self, *args, **kwargs):
        """ Initialize this object"""
        super(OrderShopify, self).__init__(*args, **kwargs)

    def _validate_self(self):
        return True

    @classmethod
    def fetch(cls, app=None, app_uuid=None, save=True):
        """Obtains a list of orders for a client from Shopify.

        The reason an app is needed is because a client's token is incorrect
        if he/she installs more than one of our products. We must use the
        app's store_token instead. (also, AppShopify has the methods)

        If save is False, returns a list of OrderShopify objects that are
        only in memory. In the case that you are querying the store for
        orders information, you should not save the orders you get. Only
        when we are responsible for the order should we save the order model.

        Max count is limited to 250.

        All parameters must be supplied as kwargs.

        Default: []
        """
        orders = []

        if not app:
            app = AppShopify.get(app_uuid)

        if not app:
            raise ValueError('Missing app/app_uuid')

        try:
            result = app._call_Shopify_API("GET", "orders.json?count=250")
            orders_json = result.get("orders")
        except (ShopifyAPIError, ValueError, AttributeError), err:
            logging.error("Shopify API failed: %s" % err, exc_info=True)
            return []  # what can you do?

        for order_json in orders_json:
            if save:
                # OrderShopify.create is actually get_or_create
                orders.append(cls.create(client=app.client,
                                         order_token=order_json['token'],
                                         order_id=str(order_json['id']),
                                         order_num=str(order_json['number']),
                                         subtotal=float(order_json['subtotal_price'])))
            else:
                orders.append(cls(order_token=order_json['token'],
                                  order_id=str(order_json['id']),
                                  client=app.client,
                                  store_name=app.client.name,
                                  store_url=app.client.url,
                                  order_number=str(order_json['number']),
                                  subtotal_price=float(order_json['subtotal_price'])))

        logging.debug('fetched %d orders' % len(orders))
        return orders

    # Constructor
    @staticmethod
    def create(user, client, order_token, order_id="", order_num="",
               subtotal=0.0, referrer=""):
        """Create an Order for a Shopify store."""

        # Don't duplicate orders!
        o = OrderShopify.get_by_token(order_token)
        if o != None:
            logging.info("Not duplicating Order %s" % (order_token))
            return o

        logging.info("Creating new Order with ref: %s" % referrer)

        uuid = generate_uuid(16)

        o = OrderShopify(key_name=uuid,
                         uuid=uuid,
                         order_token=order_token,
                         order_id=str(order_id),
                         client=client,
                         store_name=client.name,
                         store_url=client.url,
                         order_number=str(order_num),
                         subtotal_price=float(subtotal),
                         referring_site=referrer)
        if user:
            o.user = user

        o.put()

        return o

    @staticmethod
    def get_by_id(oid):
        return OrderShopify.all().filter('order_id =', str(oid)).get()

    @staticmethod
    def get_by_token(t):
        return OrderShopify.all().filter('order_token =', t).get()