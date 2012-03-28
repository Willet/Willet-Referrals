#!/usr/bin/env python

import hashlib

from google.appengine.ext   import db
from apps.client.models     import Client
from util.model             import Model

class Product(Model, db.polymodel.PolyModel):

    created = db.DateTimeProperty(auto_now_add=True)
    client  = db.ReferenceProperty(Client, collection_name='products')
    
    # name of the product ...
    title = db.StringProperty()

    # description
    description = db.TextProperty()

    # list of urls to images 
    images = db.StringListProperty()

    price = db.FloatProperty(default=float(0))

    memcache_fields = ['resource_url']

    def __init__(self, *args, **kwargs):
        self._memcache_key = kwargs['uuid'] if 'uuid' in kwargs else None 
        super(Product, self).__init__(*args, **kwargs)

    def _validate_self(self):
        return True

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
        uuid = hashlib.md5(uu_format).hexdigest()
        
        try:
            resource_url = kwargs['resource_url']
        except:
            resource_url = ''
        
        product = Product(
            key_name=uuid,
            uuid=uuid,
            title=title,
            description=description,
            images=images,
            price=price,
            client=client,
            resource_url=resource_url,
            type=type,
            tags=tags
        )
        product.put()
        return product

    @staticmethod
    def get_or_create(title, description='', images=[], tags=[], price=0.0, client=None, resource_url='', type=''):
        if client and client.domain and title: # can check for existence
            uu_format = "%s-%s" % (client.domain, title)
            uuid = hashlib.md5(uu_format).hexdigest()
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
