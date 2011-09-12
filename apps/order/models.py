#!/usr/bin/python

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc"

__all__ = [
    'ShopifyOrder'
]

import logging
from google.appengine.api import memcache
from google.appengine.ext import db

from util.model         import Model, ObjectListProperty

class ShopifyItem:

    def __init__( self, name, price, product_id ):
        self.name       = name
        self.price      = price
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
    order_token    = db.StringProperty( indexed = True )
    order_id       = db.StringProperty( indexed = True )
    created        = db.DateTimeProperty(auto_now_add=True)
    store_name     = db.StringProperty( indexed = False )
    store_url      = db.StringProperty( indexed = False, required=False, default=None )
    order_number   = db.StringProperty( indexed = False )
    subtotal_price = db.FloatProperty( indexed = False ) # no taxes
    referring_site = db.StringProperty( indexed = False, required=False, default=None ) # might be useful
    items          = ObjectListProperty( ShopifyItem, indexed=False )

    user = db.ReferenceProperty( db.Model, default = None, collection_name="shopify_purchases" )
    campaign = db.ReferenceProperty( db.Model, collection_name="shopify_orders" )

    def __init__(self, *args, **kwargs):
        self._memcache_key = kwargs['order_token'] if 'order_token' in kwargs else None 
        
        super(ShopifyOrder, self).__init__(*args, **kwargs)

    def add_item( self, item_name, item_price, item_id ):
        i = ShopifyItem( name=item_name, price=item_price, product_id=item_id )
        self.items.append( i )

        self.put()

    @staticmethod
    def _get_from_datastore( uuid ):
        """Datastore retrieval using memcache_key"""
        return db.Query(ShopifyOrder).filter('order_token =', uuid).get()

def create_shopify_order( campaign, order_token, order_id, order_num,
                          subtotal, referrer, user ):
    logging.info(referrer)
    logging.info(campaign.store_url)

    o = ShopifyOrder( key_name     = order_token,
                      order_token  = order_token,
                      order_id     = str(order_id),
                      campaign     = campaign,
                      store_name   = campaign.store_name,
                      store_url    = campaign.store_url,
                      order_number = str(order_num),
                      subtotal_price = float(subtotal), 
                      referring_site = referrer,
                      user         = user )
    o.put()

    return o # return incase the caller wants it

def get_shopify_order_by_token( order_token ):
    return ShopifyOrder.all().filter( 'order_token =', order_token ).get()
