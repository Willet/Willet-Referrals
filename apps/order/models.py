#!/usr/bin/python

# An Order Model
# Stores information about a purchase / point of conversion
# Will be subclassed

__author__ = "Willet, Inc."
__copyright__ = "Copyright 2011, Willet, Inc"

import logging
from google.appengine.ext import db
from google.appengine.ext.db import polymodel

from util.model import Model
from util.helpers import generate_uuid
from util.memcache_ref_prop import MemcacheReferenceProperty

# -----------------------------------------------------------------------------
# Order Class Definition ------------------------------------------------------
# -----------------------------------------------------------------------------
class Order(Model, polymodel.PolyModel):
    """Model storing purchase order data"""

    # Datetime when this Order was first stored in the DB
    created = db.DateTimeProperty(auto_now_add=True)

    # User who completed this Order (ie. buyer)
    user = MemcacheReferenceProperty(db.Model,
                                     default=None,
                                     collection_name="purchases")
    
    # Person who is selling the wareZ (ie. seller)
    client = db.ReferenceProperty(db.Model, collection_name="orders")
    
    # Total price of this Order (taxes not incl)
    subtotal_price = db.FloatProperty(indexed = False) # no taxes
    
    # Products that were purchased in this order
    products = db.ListProperty(db.Key)

    def __init__(self, *args, **kwargs):
        """ Initialize this object"""
        self._memcache_key = kwargs['uuid'] if 'uuid' in kwargs else None 
        
        super(Order, self).__init__(*args, **kwargs)
    
    def _validate_self(self):
        return True

    @staticmethod
    def _get_from_datastore(uuid):
        """Datastore retrieval using memcache_key"""
        return Order.all().filter('uuid =', uuid).get()

# Accessors -------------------------------------------------------------------
def get_order_by_uuid(uuid):
    return Order.all().filter('uuid =', uuid).get()
