#!/usr/bin/python

# An Order Model
# Stores information about a purchase / point of conversion
# Will be subclassed

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc"

import logging
from google.appengine.api import memcache
from google.appengine.ext import db

from util.model           import Model, ObjectListProperty

# ------------------------------------------------------------------------------
# Product Class Definition -----------------------------------------------------
# ------------------------------------------------------------------------------
class Product:
    """ A simple Product class to store some data about products
        that can be purchased """

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

# ------------------------------------------------------------------------------
# Order Class Definition -------------------------------------------------------
# ------------------------------------------------------------------------------
class Order( Model, db.PolyModel ):
    """Model storing purchase order data"""
    # A unique identifier
    uuid           = db.StringProperty( indexed = True )

    # Datetime when this Order was first stored in the DB
    created        = db.DateTimeProperty(auto_now_add=True)

    # User who completed this Order (ie. buyer)
    user           = db.ReferenceProperty( db.Model, default = None, collection_name="purchases" )
    
    # Person who is selling the wareZ (ie. seller )
    client         = db.ReferenceProperty( db.Model, collection_name="orders" )
    
    # Total price of this Order (taxes not incl)
    subtotal_price = db.FloatProperty( indexed = False ) # no taxes
    
    # Products that were purchased in this order
    products       = ObjectListProperty( Product, indexed=False )

    def __init__(self, *args, **kwargs):
        """ Initialize this object"""
        self._memcache_key = kwargs['uuid'] if 'uuid' in kwargs else None 
        
        super(Order, self).__init__(*args, **kwargs)
    
    @staticmethod
    def _get_from_datastore( uuid ):
        """Datastore retrieval using memcache_key"""
        return Order.all().filter('uuid =', uuid).get()

    def add_product( self, product_name, product_price, product_id ):
        """ Add a Product to the Order"""
        i = Product( name=product_name, price=product_price, product_id=product_id )
        self.products.append( i )

        self.put()

# Accessors --------------------------------------------------------------------
def get_order_by_uuid( uuid ):
    return Order.all().filter( 'uuid =', uuid ).get()


# ------------------------------------------------------------------------------
# OrderShopify Class Definition ------------------------------------------------
# ------------------------------------------------------------------------------
class OrderShopify( Order ):
    """Model storing shopify_order data"""
    order_token    = db.StringProperty( indexed = True )
    order_id       = db.StringProperty( indexed = True )
    order_number   = db.StringProperty( indexed = False )
    
    store_name     = db.StringProperty( indexed = False )
    store_url      = db.StringProperty( indexed = False, required=False, default=None )
    
    referring_site = db.StringProperty( indexed = False, required=False, default=None ) # might be useful

    def __init__(self, *args, **kwargs):
        """ Initialize this object"""
        super(OrderShopify, self).__init__(*args, **kwargs)

# Constructor ------------------------------------------------------------------
def create_shopify_order( client, order_token, order_id, order_num,
                          subtotal, referrer, user ):
    """ Create an Order for a Shopify store """
    
    logging.info(referrer)
    logging.info(client.store_url)

    uuid = generate_uuid( 16 )

    o = OrderShopify( key_name     = uuid,
                      uuid         = uuid,
                      order_token  = order_token,
                      order_id     = str(order_id),
                      client       = client,
                      store_name   = client.store_name,
                      store_url    = client.store_url,
                      order_number = str(order_num),
                      subtotal_price = float(subtotal), 
                      referring_site = referrer,
                      user         = user )
    o.put()

    return o # return incase the caller wants it

# Accessors --------------------------------------------------------------------
def get_shopify_order_by_token( order_token ):
    return OrderShopify.all().filter( 'order_token =', order_token ).get()
