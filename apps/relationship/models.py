#!/usr/bin/python

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc"

__all__ = [
    'Relationship'
]

import logging
from google.appengine.api import memcache
from google.appengine.ext import db

from apps.user.models import User

from util.model         import Model
from util.helpers         import generate_uuid

class Relationship(Model):
    """Model storing inter-user relationships data"""
    uuid      = db.StringProperty( indexed = True )
    created   = db.DateTimeProperty(auto_now_add=True)
    from_user = db.ReferenceProperty( db.Model, collection_name="from_relationships" )
    to_user   = db.ReferenceProperty( db.Model, default = None, collection_name=""to_relationships )
    type      = db.StringProperty( default = 'friend' )
    provider  = db.StringProperty( )

    def __init__(self, *args, **kwargs):
        self._memcache_key = kwargs['uuid'] if 'uuid' in kwargs else None 
        super(Conversion, self).__init__(*args, **kwargs)
    
    @staticmethod
    def _get_from_datastore( uuid ):
        """Datastore retrieval using memcache_key"""
        return db.Query(Relationship).filter('uuid =', uuid).get()

def create_relationship( from_u, to_u, provider = '' ):
    uuid = generate_uuid(16)
    
    r = Relationship( key_name  = uuid,
                      uuid      = uuid,
                      from_user = from_u,
                      to_user   = to_u,
                      provider  = provider
    r.put()

    return r # return incase the caller wants it

