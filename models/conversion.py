#!/usr/bin/python

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc"

__all__ = [
    'Conversion'
]

import logging
from google.appengine.api import memcache
from google.appengine.ext import db

from models.link          import get_link_by_willt_code
from models.model         import Model
from util.helpers         import generate_uuid

class Conversion(Model):
    """Model storing conversion data"""
    uuid     = db.StringProperty( indexed = True )
    created  = db.DateTimeProperty(auto_now_add=True)
    link     = db.ReferenceProperty( db.Model, collection_name="link_conversions" )
    referrer = db.ReferenceProperty( db.Model, collection_name="users_referrals" )
    referree = db.ReferenceProperty( db.Model, default = None, collection_name="users_been_referred" )
    campaign = db.ReferenceProperty( db.Model, collection_name="campaign_conversions" )

    def __init__(self, *args, **kwargs):
        self._memcache_key = kwargs['uuid'] if 'uuid' in kwargs else None 
        super(Conversion, self).__init__(*args, **kwargs)
    
    @staticmethod
    def _get_from_datastore( uuid ):
        """Datastore retrieval using memcache_key"""
        return db.Query(Conversion).filter('uuid =', uuid).get()

def create_conversion( referrer_supplied_user_id, campaign, referree ):
    link = get_link_by_supplied_user_id( referrer_supplied_user_id )

    c = Conversion( uuid     = generate_uuid(16),
                    link     = link,
                    referrer = link.user,
                    referree = referree,
                    campaign = campaign )
    c.put()

    return c # return incase the caller wants it

