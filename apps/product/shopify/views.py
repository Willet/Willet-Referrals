#!/usr/bin/env python

import logging

from apps.app.models import App
from apps.client.models import Client
from apps.product.models import Product, ProductCollection
from apps.product.shopify.models import ProductShopifyCollection

from util.urihandler import URIHandler

class SkypeCallTestingService(URIHandler):
    def get(self):
        #ProductShopifyCollection.fetch(app=App.get_by_url('http://kiehn-mertz3193.myshopify.com'))
        ProductCollection.get_or_create(collection_name="derp",
                                        products=[Product.get('09c8d1d82d90423a'),
                                                  Product.get('4b4be412fc644580'),
                                                  Product.get('59d5c07e4320492b')],
                                        client=Client.get('1b130711b754440e'))  # me

        my_col = ProductCollection.get_by_client_and_name(Client.get('1b130711b754440e'), 'derp')
        logging.debug('%r' % my_col.products)