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


class ShopifyItem:

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
    order_id = db.StringProperty( indexed = True )
    created  = db.DateTimeProperty(auto_now_add=True)
    store_name     = db.StringProperty( indexed = False )
    store_url      = db.LinkProperty( indexed = False )
    order_number   = db.StringProperty( indexed = False )
    subtotal_price = db.FloatProperty( indexed = False ) # no taxes
    referring_site = db.LinkProperty( indexed = False ) # might be useful
    items          = db.ListProperty( ShopifyItem, default = None )

    user = db.ReferenceProperty( db.Model, default = None, collection_name="shopify_purchases" )
    campaign = db.ReferenceProperty( db.Model, collection_name="shopify_orders" )

    def __init__(self, *args, **kwargs):
        self._memcache_key = kwargs['order_id'] if 'order_id' in kwargs else None 
        super(ShopifyOrder, self).__init__(*args, **kwargs)

    def add_item( self, item_name, item_price, item_id ):
        i = ShopifyItem( name=item_name, price=item_price, product_id=item_id )
        self.items.append( i )

        self.put()

    @staticmethod
    def _get_from_datastore( uuid ):
        """Datastore retrieval using memcache_key"""
        return db.Query(ShopifyOrder).filter('order_id =', uuid).get()

def create_shopify_order( campaign, order_id, order_num,
                          subtotal, referrer, user ):
    
    o = ShopifyOrder( key_name   = order_id,
                    order_id     = order_id,
                    campaign     = campaign,
                    store_name   = campaign.store_name,
                    store_url    = campaign.store_url,
                    order_number = order_num,
                    subtotal_price = subtotal, 
                    referring_site = referrer,
                    user         = user )
    o.put()

    return o # return incase the caller wants it


