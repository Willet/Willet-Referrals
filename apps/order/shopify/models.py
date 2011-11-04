#!/usr/bin/python

# An Order Model
# Stores information about a purchase / point of conversion
# Will be subclassed

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc"

import logging
from google.appengine.api    import memcache
from google.appengine.ext    import db
from google.appengine.ext.db import polymodel

from apps.order.models       import Order

from util.model              import Model
from util.helpers            import generate_uuid

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
def create_shopify_order( user, client, order_token, order_id, order_num = "",
                          subtotal = 0.0, referrer = "" ):
    """ Create an Order for a Shopify store """

    # Don't duplicate orders!
    o = get_shopify_order_by_id( order_id ) 
    if o != None:
        return o
    
    logging.info(referrer)

    uuid = generate_uuid( 16 )

    o = OrderShopify( key_name     = uuid,
                      uuid         = uuid,
                      order_token  = order_token,
                      order_id     = str(order_id),
                      client       = client,
                      store_name   = client.name,
                      store_url    = client.url,
                      order_number = str(order_num),
                      subtotal_price = float(subtotal), 
                      referring_site = referrer,
                      user         = user )
    o.put()

    return o # return incase the caller wants it

# Accessors --------------------------------------------------------------------
def get_shopify_order_by_id( id ):
    return OrderShopify.all().filter( 'order_id =', str(id) ).get()

def get_shopify_order_by_token( t ):
    return OrderShopify.all().filter( 'order_token =', t ).get()
