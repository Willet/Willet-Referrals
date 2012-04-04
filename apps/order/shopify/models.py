#!/usr/bin/python

# A subclass of Order Model
# Specific to Shopify
# Stores information about a purchase / point of conversion

__author__ = "Willet, Inc."
__copyright__ = "Copyright 2011, Willet, Inc"

import logging

from google.appengine.ext import db
from apps.order.models import Order
from util.model import Model
from util.helpers import generate_uuid

# ------------------------------------------------------------------------------
# OrderShopify Class Definition ------------------------------------------------
# ------------------------------------------------------------------------------
class OrderShopify( Order ):
    """Model storing shopify_order data"""
    order_token = db.StringProperty( indexed = True )
    order_id = db.StringProperty( indexed = True )
    order_number = db.StringProperty( indexed = False )
    
    store_name = db.StringProperty( indexed = False )
    store_url = db.StringProperty( indexed = False, required=False, default=None )
    
    referring_site = db.StringProperty( indexed = False, required=False, default=None ) # might be useful

    def __init__(self, *args, **kwargs):
        """ Initialize this object"""
        super(OrderShopify, self).__init__(*args, **kwargs)

    def _validate_self(self):
        return True

    # Constructor
    @staticmethod
    def create( user, client, order_token, order_id = "", 
                order_num = "", subtotal = 0.0, referrer = "" ):
        """ Create an Order for a Shopify store """

        # Don't duplicate orders!
        o = OrderShopify.get_by_token( order_token ) 
        if o != None:
            logging.info("Not duplicating Order %s" % (order_token))
            return o
        
        logging.info("Creating new Order with ref: %s" % referrer)

        uuid = generate_uuid( 16 )

        o = OrderShopify( key_name = uuid,
                          uuid = uuid,
                          order_token = order_token,
                          order_id = str(order_id),
                          client = client,
                          store_name = client.name,
                          store_url = client.url,
                          order_number = str(order_num),
                          subtotal_price = float(subtotal), 
                          referring_site = referrer,
                          user = user )
        o.put()

        return o # return incase the caller wants it

    # Accessors
    @staticmethod
    def get_by_id( id ):
        return OrderShopify.all().filter( 'order_id =', str(id) ).get()

    @staticmethod
    def get_by_token( t ):
        return OrderShopify.all().filter( 'order_token =', t ).get()

