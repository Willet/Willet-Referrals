#!/usr/bin/env python

import hashlib
import logging

from google.appengine.api import memcache
from google.appengine.ext import db
from apps.client.models import Client
from util.model import Model

class Product(Model, db.polymodel.PolyModel):

    created = db.DateTimeProperty(auto_now_add=True)
    client  = db.ReferenceProperty(Client, collection_name='products')
    description = db.TextProperty()
    images = db.StringListProperty() # list of urls to images 
    price = db.FloatProperty(default=float(0))
    resource_url = db.StringProperty(default = "") # product page url & main lookup key
    tags = db.StringListProperty(indexed = False) # A list of tags to describe the product
    title = db.StringProperty() # name of the product
    type = db.StringProperty(indexed = False) # The type of product

    memcache_fields = ['resource_url']

    def __init__(self, *args, **kwargs):
        self._memcache_key = kwargs['uuid'] if 'uuid' in kwargs else None 
        super(Product, self).__init__(*args, **kwargs)

    def _validate_self(self):
        return True

    @classmethod
    def _get_memcache_key (cls, unique_identifier):
        ''' unique_identifier can be URL or ID '''
        return '%s:%s' % (cls.__name__.lower(), str (unique_identifier))

    @staticmethod
    def _get_from_datastore(uuid):
        """Datastore retrieval using memcache_key"""
        return db.Query(Product).filter('uuid =', uuid).get()
    
    @staticmethod
    def create(title, description='', images=[], tags=[], price=0.0, client=None, resource_url='', type=''):
        '''Creates a product in the datastore. 
           Accepts datastore fields, returns Product object.
        '''
        if not client:
            raise AttributeError("Must have client")
        
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
        product.resource_url=resource_url # apparently had to be separate
        product.put()
        return product

    @staticmethod
    def get_or_create(title, description='', images=[], tags=[], price=0.0, client=None, resource_url='', type=''):
        if client and client.domain and title: # can check for existence
            uu_format = "%s-%s" % (client.domain, title)
            uuid = Product.build_secondary_key(uu_format)
            product = Product.get(uuid)
            if product:
                return product
        
        product = Product.create(
            title=title,
            description=description,
            images=images,
            price=price,
            client=client,
            resource_url=resource_url,
            type=type,
            tags=tags
        )
        return product

    @classmethod
    def get_by_url(cls, url):
        
        data = memcache.get(cls._get_memcache_key(url))
        if data:
            return db.model_from_protobuf(entity_pb.EntityProto(data))
        
        data = memcache.get(url)
        if data:
            return db.model_from_protobuf(entity_pb.EntityProto(data))
        
        product = cls.all().filter('resource_url =', url).get()
        return product

    @classmethod
    def get_or_fetch(cls, url, client):
        ''' returns a product from our datastore, or if it is not found AND cls is ProductShopify, 
            fire a JSON request to Shopify servers to get the product's
            information, create the Product object, and returns that.
        '''
        url = url.split('?')[0].strip('/') # removes www.abc.com/product[/?junk=...]
        product = Product.get_by_url(url)
        if not product:
            logging.error("Cannot get product (no fetch method available) from %s" % url)
        return product
