#!/usr/bin/env python

import logging

from django.utils import simplejson as json
from google.appengine.api import urlfetch, taskqueue
from google.appengine.ext import db
from google.appengine.api import memcache
from google.appengine.datastore import entity_pb

from apps.app.shopify.models import AppShopify
from apps.client.models import Client
from apps.product.models import Product, ProductCollection

from util.errors import ShopifyAPIError
from util.helpers import generate_uuid, url
from util.consts import MEMCACHE_TIMEOUT


class ProductShopifyCollection(ProductCollection):
    """A "category" of sorts that binds multiple products under one roof.

    ProductShopifyCollection contains methods necessary to fetch Shopify
    stores' collection information.
    """

    # id of this same collection on Shopify.
    shopify_id = db.StringProperty(required=True, indexed=True)

    # saving it now to be safe
    shopify_handle = db.StringProperty(required=False, indexed=False)

    def __init__(self, *args, **kwargs):
        super(ProductShopifyCollection, self).__init__(*args, **kwargs)

    def _validate_self(self):
        """."""
        self.shopify_id = unicode(self.shopify_id)
        return True

    @staticmethod
    def create(**kwargs):
        """Creates a collection in the datastore using kwargs.

        In order to save as superclass (ProductCollection), all subclasses
        must implement this exact function. Also, ProductCollection must be
        a PolyModel.
        """
        kwargs['uuid'] = kwargs.get('uuid', generate_uuid(16))
        kwargs['key_name'] = kwargs.get('uuid')

        # patch for fake python property
        if kwargs.get('products', False):
            kwargs['product_uuids'] = [x.uuid for x in kwargs.get('products')]

        obj = ProductShopifyCollection(**kwargs)
        obj.put()

        return obj

    @classmethod
    def fetch(cls, app=None, app_uuid=None, force_update=False):
        """Obtains a list of collections for a client from Shopify.

        Also fetches the products associated with this collection.
        If a collection of the same name is found, it WILL be reused.

        The reason an app is needed is because a client's token is incorrect
        if he/she installs more than one of our products. We must use the
        app's store_token instead. (also, AppShopify has the methods)

        Either app or app_uuid must be supplied as kwargs.

        Default: []
        """
        collections = []

        if not app:
            app = AppShopify.get(app_uuid)

        if not app:
            raise ValueError('Missing app/app_uuid')

        # calling AppShopify's private member
        # (getting product collections are hardly an app's job)
        result = app._call_Shopify_API(verb="GET",
                                       call="custom_collections.json")
        logging.debug('result = %r' % result, exc_info=True)

        if not result:
            raise ShopifyAPIError("No custom collection data was returned: "
                                  "%s" % result,
                                  exc_info=True)

        collections_jsons = result.get('custom_collections', False)
        if not collections_jsons:
            raise ShopifyAPIError("Custom collection data is malformed: "
                                  "%s" % result,
                                  exc_info=True)

        for collection_json in collections_jsons:
            # use old one or make new one
            collection = cls.get_by_shopify_id(collection_json['id'])
            if not collection:
                logging.warn("No collection found by id "
                             "%s" % collection_json['id'])
                collection = cls.create(client=app.client,
                                        collection_name=collection_json['title'],
                                        shopify_id=unicode(collection_json['id']),
                                        shopify_handle=collection_json['handle'],
                                        products=[])
            collections.append(collection)

        for collection in collections:
            taskqueue.add(url=url('PutShopifyCollections'), params={
                "col_uuid": collection.uuid,
                "app_uuid": app.uuid,
                "force": str(force_update)
            })

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
            app = AppShopify.get(app_uuid)

        if not app:
            raise ValueError('Missing app/app_uuid')

        collections = app.client.collections  # db.Query object?!
        logging.debug('client.collections = %r' % collections)
        if not collections:
            logging.debug('Client has no collections; fetching.')
        collections = cls.fetch(app=app, app_uuid=app_uuid)

        return collections

    def fetch_products(self, app=None, app_uuid=None):
        """Retrieve Shopify products under this collection.

        Products need to already exist in the database.
        """
        products = []

        if not app:
            app = AppShopify.get(app_uuid)

        if not app:
            raise ValueError('Missing app/app_uuid')

        # calling AppShopify's private member
        # (getting product collections are hardly an app's job)
        result = app._call_Shopify_API(
            verb="GET", call="products.json?collection_id=%s" % self.shopify_id)

        if not result:
            raise ShopifyAPIError("No product data was returned: %s" % result,
                                  exc_info=True)
        logging.info("products = %r" % result)

        products_jsons = result.get('products', False)
        if not products_jsons:
            raise ShopifyAPIError("Product data is malformed: %s" % result,
                                  exc_info=True)

        # fetch all products regardless.
        # http://kiehn-mertz3193.myshopify.com/admin/products/{ id }.json
        for product_json in products_jsons:
            pid = product_json['id']
            product = ProductShopify.get_by_shopify_id(pid)
            if not product:  # create if not exists
                result = app._call_Shopify_API(verb="GET",
                                               call="products/%s.json" % pid)
                product = ProductShopify.create_from_json(client=app.client,
                                                          data=result['product'])

            product.collections.append(self)
            product.put()  # commitment last
            products.append(product)

        return products

    def get_or_fetch_products(self, app=None, app_uuid=None,
                              force_update=False):
        """Retrieve Shopify products under this collection."""
        if not self.products or force_update:
            self.products = self.fetch_products(app=app, app_uuid=app_uuid)
            self.put()  # commitment last
        return self.products

    @classmethod
    def get_by_shopify_id(cls, cid):
        """Scrapes the datastore for a collection by shopify_id."""
        collection = None
        cid = unicode(cid)

        try:
            collection = cls.all().filter('shopify_id =', cid).get()

        # whatever exception it is when a query returns 0 results and you
        # try to get() it
        except Exception, err:
            logging.error('oh no: %s' % err, exc_info=True)

        return collection


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

        if not product.resource_url and not data.get("url"):
            # Create the product URL
            # {client.url}/products/{handle}

            url = "%s/products/%s" % (client.domain.lower(), data.get("handle"))
            data["url"] = url

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
        if data.get("url"):
            self.resource_url = data.get("url")

        if hasattr(self, 'processed'):
            delattr(self, 'processed')

        self.put()

    def add_url(self, url):
        """ The Shopify API doesn't give us the URL for the product.
            Just add it here """
        self.resource_url = url
        self.put()
