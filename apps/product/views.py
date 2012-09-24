#!/usr/bin/env python

import logging

from django.utils import simplejson as json

from apps.client.models import Client
from apps.product.models import Product, ProductCollection
from apps.product.shopify.models import ProductShopifyCollection

from util.urihandler import obtain, URIHandler


class CollectionJSONDynamicLoader(URIHandler):
    """Retrieve information about collections. Output is JSON."""
    @obtain('collection_uuid', 'collection_shopify_id', 'client_uuid',
            'collection_name')
    def get(self, collection_uuid, collection_shopify_id, client_uuid,
            collection_name):
        """Retrieve information about collections. Output is an array of
        collections JSON.

        Params you can use to fetch the collection:
        - collection_uuid
        - collection_shopify_id
        - client_uuid
        - client_uuid & collection_name
        """
        collections = filter(None, [ProductCollection.get(collection_uuid)])
        if len(collections):
            return self.jsonify(collections)

        collections = filter(None, [ProductShopifyCollection.get_by_shopify_id(
            collection_uuid)])
        if len(collections):
            return self.jsonify(collections)

        client = Client.get(client_uuid)
        if client:
            if collection_name:  # specified collection
                for collection in client.collections:
                    if collection.collection_name == collection_name:
                        return self.jsonify([collection])
            else:  # no specific name
                return self.jsonify(filter(None, client.collections))

        return self.jsonify([])  # nothing

    def post(self):
        """ TODO: make API to allow collection modification """
        pass

    def jsonify(self, collections):
        """PRINTS out a json object for the collections supplied:
        {
            collections: [
                { ... },
                { ... },
                ...
            ]
        }
        """

        # Decode an encoded json object, because I'm an idiot
        cols_json = [json.loads(col.to_json()) for col in collections if col]
        json_base = {'collections': cols_json}

        self.response.out.write(json.dumps(json_base))
        return


class ProductJSONDynamicLoader(URIHandler):
    """Retrieve information about products. Output is JSON."""
    @obtain('product_uuid', 'product_shopify_id', 'client_uuid', 'collection_uuid')
    def get(self, product_uuid, product_shopify_id, client_uuid, collection_uuid):
        """Retrieve information about products. Output is an array of
        products JSON.

        Params you can use to fetch the product:
        - product_uuid
        - product_shopify_id
        - client_uuid
        - collection_uuid
        """
        products = [Product.get(product_uuid)]
        if len(products):
            return self.jsonify(products)

        products = [ProductShopify.get_by_shopify_id(product_uuid)]
        if len(products):
            return self.jsonify(products)

        client = Client.get(client_uuid)
        if client:
            return self.jsonify(client.products)

        collection = ProductCollection.get(collection_uuid)
        if collection:
            return self.jsonify(collection.products)

        return self.jsonify([])  # nothing

    def post(self):
        """ TODO: make API to allow product modification """
        pass

    def jsonify(self, products):
        """PRINTS out a json object for the products supplied.

        The json format mimics the shopify product json, but not exactly.
        (I am trying to make your life worse, lololo)
        """
        products_json = [json.loads(product.to_json()) for product in products]
        json_base = {'products': products_json}
        self.response.out.write(json.dumps(json_base))
        return
