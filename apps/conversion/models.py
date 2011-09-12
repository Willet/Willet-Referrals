#!/usr/bin/python

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc"

__all__ = [
    'Conversion'
]

import logging
from google.appengine.api import memcache
from google.appengine.ext import db

from apps.link.models import get_link_by_willt_code
from util.model         import Model
from util.helpers         import generate_uuid

class Conversion(Model):
    """Model storing conversion data"""
    uuid     = db.StringProperty( indexed = True )
    created  = db.DateTimeProperty(auto_now_add=True)
    link     = db.ReferenceProperty( db.Model, collection_name="link_conversions" )
    referrer = db.ReferenceProperty( db.Model, collection_name="users_referrals" )
    referree = db.ReferenceProperty( db.Model, default = None, collection_name="users_been_referred" )
    referree_uid = db.StringProperty()
    campaign = db.ReferenceProperty( db.Model, collection_name="campaign_conversions" )
    order = db.StringProperty()

    def __init__(self, *args, **kwargs):
        self._memcache_key = kwargs['uuid'] if 'uuid' in kwargs else None 
        super(Conversion, self).__init__(*args, **kwargs)
    
    @staticmethod
    def _get_from_datastore( uuid ):
        """Datastore retrieval using memcache_key"""
        return db.Query(Conversion).filter('uuid =', uuid).get()

def create_conversion( link, campaign, referree_uid, referree, order_num ):
    uuid = generate_uuid(16)
    
    c = Conversion( key_name     = uuid,
                    uuid         = uuid,
                    link         = link,
                    referrer     = link.user,
                    referree     = referree,
                    referree_uid = referree_uid,
                    campaign     = campaign,
                    order        = order_num )
    c.put()

    return c # return incase the caller wants it

