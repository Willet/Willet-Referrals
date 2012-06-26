#!/usr/bin/env python

import logging

from django.utils import simplejson as json

from apps.app.models import App
from apps.client.models import Client
from apps.client.shopify.models import ClientShopify
from apps.product.models import Product
from apps.product.shopify.models import ProductShopify, ProductShopifyCollection

from util.shopify_helpers import get_shopify_url
from util.urihandler import obtain, URIHandler


class CreateProductShopify(URIHandler):
    """Create a Shopify product"""
    def post(self):
        logging.info("HEADERS : %s %r" % (
            self.request.headers,
            self.request.headers
            )
        )

        store_url = get_shopify_url(self.request.headers['X-Shopify-Shop-Domain'])
        logging.info("store: %s " % store_url)
        client = ClientShopify.get_by_url(store_url)

        # Grab the data about the product from Shopify
        product = json.loads(self.request.body)

        ProductShopify.create_from_json(client, product)


class UpdateProductShopify(URIHandler):
    """Update a Shopify product"""
    def post(self):
        logging.info("HEADERS : %s %r" % (
            self.request.headers,
            self.request.headers
            )
        )

        store_url = "http://%s" % self.request.headers['X-Shopify-Shop-Domain']
        logging.info("store: %s " % store_url)
        store_url = get_shopify_url(self.request.headers['X-Shopify-Shop-Domain'])

        # Grab the data about the product from Shopify
        data = json.loads(self.request.body)
        product = ProductShopify.get_by_shopify_id(str(data['id']))

        if product:
            product.update_from_json(data)
        else:
            client = ClientShopify.get_by_url(store_url)
            ProductShopify.create_from_json(client, data)


class DeleteProductShopify(URIHandler):
    """Delete a Shopify product"""
    def post(self):
        logging.info("HEADERS : %s %r" % (
            self.request.headers,
            self.request.headers
            )
        )

        # Grab the data about the product from Shopify
        data = json.loads(self.request.body)

        product = ProductShopify.get_by_shopify_id(str(data['id']))

        # Delete the product from our DB.
        if product:
            product.delete()


class FetchShopifyProducts(URIHandler):
    """Query the Shopify API to fetch all Products. Used by taskqueues."""
    def get (self):
        self.post()

    def post(self):
        """Given client or client_uuid both as uuid"""
        logging.info("RUNNING product.shopify.processes::FetchShopifyProducts")

        client = ClientShopify.get(self.request.get('client'))
        if not client:
            client = ClientShopify.get(self.request.get('client_uuid'))

        if client:
            app_type = self.request.get('app_type')
            client.get_products(app_type)
            self.response.out.write("OK")
        else:
            logging.error('Client cannot be found.')


class FetchShopifyCollections(URIHandler):
    """Make a shopify store fetch its collections if none exist.

    Can be used by taskqueues."""
    def get (self):
        self.post()

    def post(self):
        """Make a shopify store fetch its collections if none exist.

        Required parameters (either one):
            store_url (e.g. http://ohai.ca)
            app_uuid

        Optional parameters:
            force (if anything is supplied for this param, collections will be
            force-fetched)
        """
        logging.info("RUNNING product.shopify.processes::FetchShopifyCollections")
        app_uuid = self.request.get('app_uuid', '')
        force = self.request.get('force', False)

        app = App.get(app_uuid)

        if not app:
            store_url = self.request.get('store_url', '')
            app = App.get_by_url(store_url)

        if app:
            if bool(force) == True:
                my_cols = ProductShopifyCollection.fetch(app=app)
            else:  # get or create
                my_cols = ProductShopifyCollection.get_or_fetch(app=app)

            if my_cols:
                self.response.out.write("OK")
            else:
                logging.warn('Found no collections')
        else:
            logging.warn('Found no app by the url %s' % store_url)

        return