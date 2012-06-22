#!/usr/bin/env python

import logging

from django.utils import simplejson as json
from google.appengine.api import urlfetch
from google.appengine.ext import db
from google.appengine.api import memcache
from google.appengine.datastore import entity_pb

from apps.client.models import Client
from apps.product.models import Product, ProductCollection
from util.errors import ShopifyAPIError
from util.helpers import generate_uuid
from util.consts import MEMCACHE_TIMEOUT


class ProductShopifyCollection(ProductCollection):
    """A "category" of sorts that binds multiple products under one roof.

    ProductShopifyCollection contains methods necessary to fetch Shopify
    stores' collection information.
    """
    shopify_id = db.IntegerProperty(required=True, indexed=True)

    @classmethod
    def fetch(cls, app=None, app_uuid=None):
        """Obtains a list of collections for a client from Shopify.

        The reason an app is needed is because a client's token is incorrect
        if he/she installs more than one of our products. We must use the
        app's store_token instead.

        Either app or app_uuid must be supplied as kwargs.

        Default: []
        """
        collections = []

        if not app:
            app = App.get(app_uuid)

        if not app:
            raise ValueError('Missing app/app_uuid')

        # calling AppShopify's private member
        # (getting product collections are hardly an app's job)
        result = app._call_Shopify_API(verb="GET",
                                       call="custom_collections.json")

        if not result:
            raise ShopifyAPIError("No custom collection data was returned: "
                                  "%s" % result,
                                  exc_info=True)
        logging.error("%r" % result)

        collections_jsons = result.get('custom_collections', False)
        if not collections_jsons:
            raise ShopifyAPIError("Custom collection data is malformed: "
                                  "%s" % result,
                                  exc_info=True)

        collection_ids = [collection_json['id'] \
                          for collection_json in collections_jsons]

        collections = [cls(shopify_id=collection_id) \
                       for collection_id in collection_ids]

        for collection in collections:
            collection.put()  # save them all

        return collections

    @classmethod
    def get_or_fetch(cls, app=None, app_uuid=None):
        """Given either the app or its uuid, generate all CustomCollection
        objects ("collections") in his/her Shopify account.

        Argument positions may change. This must be called with keywords.

        Default: []

        WARNING there are no CustomCollection webhooks. This information can
        be outdate very quickly.
        """
        collections = []

        if not app:
            app = App.get(app_uuid)

        if not app:
            raise ValueError('Missing app/app_uuid')

        collections = app.client.collections  # can be parent class
        if not collections:
            collections = cls.fetch(client=client)

        return collections

    def fetch_products(self, app=None, app_uuid=None):
        """Retrieve Shopify products under this collection."""
        if not app:
            app = App.get(app_uuid)

        if not app:
            raise ValueError('Missing app/app_uuid')

        # calling AppShopify's private member
        # (getting product collections are hardly an app's job)
        result = app._call_Shopify_API(
            verb="GET", call="products.json?collection_id=%d" % self.shopify_id)

        if not result:
            raise ShopifyAPIError("No product data was returned: %s" % result,
                                  exc_info=True)
        logging.error("%r" % result)

        products_jsons = result.get('products', False)
        if not products_jsons:
            raise ShopifyAPIError("Product data is malformed: %s" % result,
                                  exc_info=True)

        product_ids = [product_json['id'] for product_json in product_jsons]

        products = [Product.get_or_fetch(product_id) for product_id in product_ids]

        for product in products:
            product.collection = self
            product.put()  # save them all

        return products

    def get_or_fetch_products(self, app=None, app_uuid=None):
        """Retrieve Shopify products under this collection."""


class ProductShopify(Product):
    """Methods for manipulating our copies of Shopify products."""
    shopify_id = db.StringProperty(indexed=True)

    _memcache_fields = ['resource_url', 'shopify_id']

    def __init__(self, *args, **kwargs):
        super(ProductShopify, self).__init__(*args, **kwargs)

    def _validate_self(self):
        # Could check if shopify_id is valid
        # Could check if resource_url is valid
        return True

    @staticmethod
    def create_from_json(client, data, url=None):
        # Don't make it if we already have it
        product = ProductShopify.get_by_shopify_id(str(data['id']))
        if not product:
            uuid = generate_uuid(16)

            images = []
            if 'images' in data:
                logging.debug ('%d images for this product found; adding to \
                    ProductShopify object.' % len(data['images']))
                images = [str(image['src']) for image in data['images']]

            # Make the product
            product = ProductShopify(key_name=uuid,
                                     uuid=uuid,
                                     client=client,
                                     resource_url=url,
                                     images=images)

        # Now, update it with info.
        # update_from_json will PUT the obj.
        product.update_from_json(data)
        return product

    @classmethod
    def get_by_shopify_id(cls, id):
        id = str(id)
        data = memcache.get(cls._get_memcache_key(id))
        if data:
            product = db.model_from_protobuf(entity_pb.EntityProto(data))
        else:
            product = cls.all().filter('shopify_id =', id).get()

        return product

    @classmethod
    def get_or_fetch(cls, url, client):
        """ returns a product from our datastore, or if it is not found AND cls is ProductShopify,
            fire a JSON request to Shopify servers to get the product's
            information, create the Product object, and returns that.
        """
        if not url:
            logging.error('Cannot fetch product with blank URL!')
            return None

        url = url.split('?')[0].strip('/') # removes www.abc.com/product[/?junk=...]
        product = Product.get_by_url(url)
        if not product:
            logging.warn('Could not get product for url: %s' % url)
            try:
                # for either reason, we have to obtain the new product JSON
                result = urlfetch.fetch(url='%s.json' % url,
                                        method=urlfetch.GET)
                # data is the 'product' key within the JSON object: http://api.shopify.com/product.html
                data = json.loads(result.content)['product']
                product = ProductShopify.get_by_shopify_id(str(data['id']))
                if product:
                    product.add_url(url)
                else:
                    logging.warn('failed to get product for id: %s; creating one.' % str(data['id']))
                    product = ProductShopify.create_from_json(client, data, url=url)
            except ValueError:
                logging.warn("No JSON equivalent for this page: %s" % url,
                             exc_info=True)
            except:
                logging.error("error fetching and storing product for url %s" % url,
                              exc_info=True)
        return product

    def update_from_json(self, data):
        logging.info("data %s" % data)
        tags = description = images = None
        price = 0.0

        # remove all newlines from description
        try:
            description = data['body_html']\
                    .replace('\r\n', '')\
                    .replace('\n', '')
        except:
            logging.info("No desc for this product %s" % self.uuid)

        # create a list of urls to images
        try:
            images = [image['src'] for image in data['images']]
        except:
            logging.info("No images for this product %s" % self.uuid)

        try:
            price = float(data['variants'][0]['price'])
        except:
            logging.info("No price for this product %s" % self.uuid)

        try:
            tags = data[ 'tags' ].split(',')
        except:
            logging.info("No tags for this product %s" % self.uuid)

        type = data[ 'product_type' ]


        # Update the Product
        self.shopify_id = str(data['id'])
        self.title = data[ 'title' ]
        self.json_response = json.dumps(data)

        if type:
            self.type = type
        if price != 0.0:
            self.price = price
        if images:
            self.images = images
        if description:
            self.description = description
        if tags:
            self.tags = tags

        if hasattr(self, 'processed'):
            delattr(self, 'processed')

        self.put()

    def add_url(self, url):
        """ The Shopify API doesn't give us the URL for the product.
            Just add it here """
        self.resource_url = url
        self.put()
