#!/usr/bin/env python

__author__ = "Willet, Inc."
__copyright__ = "Copyright 2011, Willet, Inc"

import hashlib
import logging

from django.utils import simplejson as json
from google.appengine.api import urlfetch

from apps.app.models import App
from apps.client.models import Client
from apps.client.shopify.models import ClientShopify
from apps.order.shopify.models import OrderShopify
from apps.product.shopify.models import ProductShopify
from apps.user.models import User

from util import httplib2
from util.helpers import *
from util.urihandler import URIHandler

class CreateShopifyOrder(URIHandler):
    def get(self):
        # Grab the important peeps
        user = User.get_by_cookie(self)
        client = Client.get(self.request.get('client_uuid'))

        # Grab order deets
        order_id = self.request.get('order_id')
        order_num = self.request.get('order_num')
        subtotal = self.request.get('subtotal')
        ref_site = self.request.get('ref_site')
        email = self.request.get('email')
        name = self.request.get('name')
        marketing = self.request.get('marketing')

        # Grab the products
        items = []
        num_items = self.request.get('num_items')
        for i in range(0, int(num_items)):
            product = ProductShopify.get_by_shopify_id(str(self.request.get('item%d' % i)))
            if product:
                items.append(product.key())

        # Make the Order
        o = OrderShopify.create(user = user,
                                 client = client,
                                 order_token = '', # Phasing this out.
                                 order_id = order_id,
                                 order_num = order_num,
                                 subtotal = subtotal,
                                 referrer = ref_site)

        # Store the purchased items in the order
        o.products.extend(items)
        o.put()

        # Update the User's info
        if user:
            user.update(first_name = name.split(' ')[0],
                        last_name = name.split(' ')[1],
                        full_name = name,
                        email = email,
                        accepts_marketing = marketing)
        else:
            logging.warn('NO USER: ')
