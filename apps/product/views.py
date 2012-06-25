#!/usr/bin/env python

import logging

from django.utils import simplejson as json

from apps.client.models import Client
from apps.product.models import Product, ProductCollection
from apps.product.shopify.models import ProductShopifyCollection

from util.urihandler import obtain, URIHandler


class CollectionDynamicLoader(URIHandler):
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
        collections = [ProductCollection.get(collection_uuid)]
        if len(collections):
            return self.jsonify(collections)

        collections = [ProductShopifyCollection.get_by_shopify_id(collection_uuid)]
        if len(collections):
            return self.jsonify(collections)

        client = Client.get(client_uuid)
        if client:
            if collection_name:  # specified collection
                for collection in client.collections:
                    if collection.collection_name == collection_name:
                        return self.jsonify([collection])
            else:  # no specific name
                return self.jsonify(client.collections)

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
        json_base = {'collections': []}
        for collection in collections:
            collection_json = {
                'uuid': collection.uuid,
                'name': collection.collection_name,
                'shopify_id': unicode(getattr(collection, 'shopify_id', '')),
                'shopify_handle': getattr(collection, 'shopify_handle', ''),
                'products': [x.uuid for x in collection.products],  # could be nothing!
            }
            json_base['collections'].append(collection_json)

        self.response.out.write(json.dumps(json_base))
        return


class ProductDynamicLoader(URIHandler):
    """Retrieve information about products. Output is JSON."""
    @obtain('product_uuid', 'product_shopify_id', 'client_uuid')
    def get(self, product_uuid, product_shopify_id, client_uuid):
        """Retrieve information about products. Output is an array of
        products JSON.

        Params you can use to fetch the product:
        - product_uuid
        - product_shopify_id
        - client_uuid
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

        return self.jsonify([])  # nothing

    def post(self):
        """ TODO: make API to allow product modification """
        pass

    def jsonify(self, products):
        """PRINTS out a json object for the products supplied:
        {
            "products": [{
                "uuid": "a2a0e0c3f1f34c9b",
                "tags": ["Demo", " T-Shirt"],
                "shopify_id": "75473022",
                "client_uuid": "1b130711b754440e",
                "title": "Secured non-volatile challenge",
                "shopify_handle": "",
                "images": [],
                "resource_url": "",
                "type": "Shirts",
                "price": "19.0",
                "description": "<p>So this is a product.<\/p><p>The..."
            }]
        }

        The json format mimics the shopify product json, but not exactly.
        (I am trying to make your life worse, lololo)
        """
        json_base = {'products': []}
        for product in products:
            product_json = {
                'uuid': product.uuid,
                'client_uuid': product.client.uuid,
                'shopify_id': unicode(getattr(product, 'shopify_id', '')),
                'shopify_handle': getattr(product, 'shopify_handle', ''),
                'images': getattr(product, 'images', []),
                'description': product.description,
                'price': unicode(product.price),
                'resource_url': product.resource_url or '',
                'tags': getattr(product, 'tags', []),
                'title': product.title,
                'type': product.type or '',
            }
            json_base['products'].append(product_json)

        self.response.out.write(json.dumps(json_base))
        return