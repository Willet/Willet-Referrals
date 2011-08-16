#!/usr/bin/python

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc"

__all__ = [
    'ShopifyOrder'
]

import logging
from google.appengine.api import memcache
from google.appengine.ext import db

from models.link          import get_link_by_willt_code
from models.model         import Model
from util.helpers         import generate_uuid


class Item:

    def __init__( self, name, price, product_id ):
        self.name  = name
        self.price = price
        self.product_id = product_id 

    def serialize( self ):
        ret = '%s@%s@%s' % (self.name, self.price, self.product_id)
        return ret

    @classmethod
    def deserialize(cls, value):
        [name, price, product_id] = value.split( '@', 2 )
        return cls( name = name, price = float(price), product_id = product_id )

class ShopifyOrder(Model):
    """Model storing shopify_order data"""
    uuid     = db.StringProperty( indexed = True )
    created  = db.DateTimeProperty(auto_now_add=True)

    store_name
    store_url
    order_number
    subtotal_price # no taxes
    referring_site # might be useful


    items ..

    user = db.ReferenceProperty( db.Model, default = None, collection_name="shopify_purchases" )
    campaign = db.ReferenceProperty( db.Model, collection_name="shopify_orders" )

    def __init__(self, *args, **kwargs):
        self._memcache_key = kwargs['uuid'] if 'uuid' in kwargs else None 
        super(ShopifyOrder, self).__init__(*args, **kwargs)
    
    @staticmethod
    def _get_from_datastore( uuid ):
        """Datastore retrieval using memcache_key"""
        return db.Query(ShopifyOrder).filter('uuid =', uuid).get()

def create_shopify_order( link, campaign, referree_uid, referree ):
    uuid = generate_uuid(16)
    
    c = ShopifyOrder( key_name     = uuid,
                    uuid         = uuid,
                    link         = link,
                    referrer     = link.user,
                    referree     = referree,
                    referree_uid = referree_uid,
                    campaign     = campaign )
    c.put()

    return c # return incase the caller wants it

