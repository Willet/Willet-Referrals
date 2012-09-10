#!/usr/bin/env python

import logging

from django.utils import simplejson as json

from apps.app.shopify.models import App, AppShopify

AppShopify
from apps.client.shopify.models import ClientShopify
from apps.product.shopify.models import ProductShopify, ProductShopifyCollection

from util.shopify_helpers import get_shopify_url
from util.urihandler import URIHandler

def create_product(request):
    logging.info("HEADERS : %s %r" % (request.headers, request.headers))

    store_url = get_shopify_url(request.headers['X-Shopify-Shop-Domain'])
    logging.info("store: %s " % store_url)
    client = ClientShopify.get_by_url(store_url)

    # Grab the data about the product from Shopify
    product = json.loads(request.body)

    new_product = ProductShopify.create_from_json(client, product)
    return new_product

def update_product(request):
    logging.info("HEADERS : %s %r" % (request.headers, request.headers))

    store_url = "http://%s" % request.headers['X-Shopify-Shop-Domain']
    logging.info("store: %s " % store_url)
    store_url = get_shopify_url(request.headers['X-Shopify-Shop-Domain'])

    # Grab the data about the product from Shopify
    data = json.loads(request.body)
    product = ProductShopify.get_by_shopify_id(str(data['id']))

    if product:
        product.update_from_json(data)
    else:
        client  = ClientShopify.get_by_url(store_url)
        product = ProductShopify.create_from_json(client, data)

    return product

def delete_product(request):
    logging.info("HEADERS : %s %r" % (request.headers, request.headers))

    # Grab the data about the product from Shopify
    data = json.loads(request.body)

    product = ProductShopify.get_by_shopify_id(str(data['id']))

    # Delete the product from our DB.
    if product:
        product.delete()

def create_collection(request):
    update_collection(request)

def update_collection(request, force_update=False):
    logging.info("HEADERS : %s %r" % (request.headers, request.headers))

    store_url = request.headers['X-Shopify-Shop-Domain']
    app       = App.get_by_url(store_url)

    # TODO: Verify that this works for non-custom collections as well.
    collections = ProductShopifyCollection.fetch(app=app, force_update=force_update)
    return collections

def delete_collection(request):
    logging.info("HEADERS : %s %r" % (request.headers, request.headers))
    # TODO: Delete collection

class CreateProductShopify(URIHandler):
    """Create a Shopify product"""
    def post(self):
        create_product(self.request)


class UpdateProductShopify(URIHandler):
    """Update a Shopify product"""
    def post(self):
        update_product(self.request)


class DeleteProductShopify(URIHandler):
    """Delete a Shopify product"""
    def post(self):
        delete_product(self.request)


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


class PutShopifyCollections(URIHandler):
    """Create collections via a taskqueue

    Fetching can be expensive. So, we divy up some of the work by putting it
    on taskqueues
    """

    def get(self):
        self.post()

    def post(self):
        """Get or fetch the products, and update the collection:

        Required parameters:
            app_uuid (the app uuid)
            col_uuid (the collection uuid)

        Optional parameters:
            force (if "True" is supplied, we force an update if products)
        """
        app_uuid = self.request.get("app_uuid")
        col_uuid = self.request.get("col_uuid")
        force    = (self.request.get("force") == "True")

        logging.info("App uuid: %s" % app_uuid)
        logging.info("Col uuid: %s" % col_uuid)
        logging.info("Force: %s"    % force)

        app        = App.get(app_uuid)
        collection = ProductShopifyCollection.get(col_uuid)

        if not app_uuid:
            logging.error("No app_uuid provided")
            return

        if not col_uuid:
            logging.error("No col_uuid provided")
            return

        if not app:
            logging.error("No app found for app_uuid '%s'" % app_uuid)
            return

        if not collection:
            logging.error("No collection found for col_uuid '%s'" % col_uuid)
            return

        collection.get_or_fetch_products(
            app=app, app_uuid=app_uuid, force_update=force
        )
        collection.put()