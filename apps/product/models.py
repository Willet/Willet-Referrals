#!/usr/bin/env python

import logging

from google.appengine.api import memcache
from google.appengine.ext import db
from apps.client.models import Client

from util.model import Model
from util.shopify_helpers import get_url_variants


class Product(Model, db.polymodel.PolyModel):
    """Stores information about a store's product."""
    created = db.DateTimeProperty(auto_now_add=True)
    client = db.ReferenceProperty(Client, collection_name='products')
    description = db.TextProperty()
    images = db.StringListProperty()  # list of urls to images
    price = db.FloatProperty(default=float(0))

    # product page url & main lookup key
    resource_url = db.StringProperty(default="")

    # A list of tags to describe the product
    tags = db.StringListProperty(indexed=False)
    title = db.StringProperty()  # name of the product
    type = db.StringProperty(indexed=False)  # The type of product

    _memcache_fields = ['resource_url', 'shopify_id']

    def __init__(self, *args, **kwargs):
        self._memcache_key = kwargs['uuid'] if 'uuid' in kwargs else None
        super(Product, self).__init__(*args, **kwargs)

    def _validate_self(self):
        return True

    @classmethod
    def _get_memcache_key (cls, unique_identifier):
        """ unique_identifier can be URL or ID """
        return '%s:%s' % (cls.__name__.lower(), str (unique_identifier))

    @staticmethod
    def _get_from_datastore(uuid):
        """Datastore retrieval using memcache_key"""
        return db.Query(Product).filter('uuid =', uuid).get()

    @staticmethod
    def create(title, description='', images=None, tags=None, price=0.0,
               client=None, resource_url='', type=''):
        """Creates a product in the datastore.
           Accepts datastore fields, returns Product object.
        """
        if not client:
            raise AttributeError("Must have client")
        if images == None:
            images = []
        if tags == None:
            tags = []

        # set uuid to its most "useful" hash.
        uu_format = "%s-%s" % (client.domain, title)
        uuid = Product.build_secondary_key(uu_format)

        product = Product(
            key_name=uuid,
            uuid=uuid,
            title=title,
            description=description,
            images=images,
            price=price,
            client=client,
            type=type,
            tags=tags
        )
        product.resource_url = resource_url # apparently had to be separate
        product.put()
        return product

    @staticmethod
    def get_or_create(title, description='', images=None, tags=None, price=0.0,
                      client=None, resource_url='', type=''):
        if images == None:
            images = []
        if tags == None:
            tags = []

        if client and client.domain and title:  # can check for existence
            uu_format = "%s-%s" % (client.domain, title)
            uuid = Product.build_secondary_key(uu_format)
            product = Product.get(uuid)
            if product:
                return product

        product = Product.create(title=title,
                                 description=description,
                                 images=images,
                                 price=price,
                                 client=client,
                                 resource_url=resource_url,
                                 type=type,
                                 tags=tags)
        return product

    @classmethod
    def get_by_url(cls, url):
        """Retrieves a Product or its subclass instance by resource_url."""
        www_url = url

        if not url:
            return None  # can't get by url if no URL given

        (url, www_url) = get_url_variants(url, keep_path=True)

        data = memcache.get(cls._get_memcache_key(url))
        if data:
            return db.model_from_protobuf(entity_pb.EntityProto(data))

        data = memcache.get(cls._get_memcache_key(www_url))
        if data:
            return db.model_from_protobuf(entity_pb.EntityProto(data))

        data = memcache.get(url)
        if data:
            return db.model_from_protobuf(entity_pb.EntityProto(data))

        data = memcache.get(www_url)
        if data:
            return db.model_from_protobuf(entity_pb.EntityProto(data))

        product = cls.all().filter('resource_url IN', [url, www_url]).get()
        return product

    @classmethod
    def get_or_fetch(cls, url, client):
        """Returns a product from our datastore.

        If the product cannot be found in the datastore, various methods will
        be used to retrieve the product. The return object class will be that
        resulted from a successful fetch.

        Examples:
            - in DB -> Product
            - not in DB, fetch like ProductShopify succeeds: ProductShopify
                (returned as Product)
            - not in DB, fetch like ProductShopify fails: None
        """
        # put there to prevent circular reference
        from apps.product.shopify.models import ProductShopify

        # remove www.abc.com/product[/?junk=...]
        url = url.split('?')[0].strip('/')

        product = Product.get_by_url(url)
        if not product:
            product = ProductShopify.get_or_fetch(url, client)

        return product
