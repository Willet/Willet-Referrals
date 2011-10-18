#!/usr/bin/env python

from google.appengine.ext import db

from apps.client.models import Client

from util.model import Model

class Product(Model, db.polymodel.PolyModel):
    uuid    = db.StringProperty(indexed=True)
    created = db.DateTimeProperty(auto_now_add=True)
    client  = db.ReferenceProperty(Client, collection_name='products')
    
    # name of the product ...
    title = db.StringProperty()

    # description
    description = db.TextProperty()

    # list of urls to images 
    images = db.StringListProperty()

    price = db.FloatProperty(default=float(0))

    def __init__(self, *args, **kwargs):
        self._memcache_key = kwargs['uuid'] if 'uuid' in kwargs else None 
        super(Product, self).__init__(*args, **kwargs)

