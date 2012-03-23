#!/usr/bin/python

# client models
# data models for our clients and associated methods

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc"

import hashlib, logging, urllib, urllib2

from datetime               import datetime
from decimal                import *
from django.utils           import simplejson as json
from google.appengine.api   import memcache
from google.appengine.api   import urlfetch
from google.appengine.api   import taskqueue
from google.appengine.ext   import db
from google.appengine.ext.db import polymodel

from apps.user.models       import *
from util.consts            import *
from util.model             import Model
from util.helpers           import generate_uuid

# ------------------------------------------------------------------------------
# Client Class Definition ------------------------------------------------------
# ------------------------------------------------------------------------------
class Client(Model, polymodel.PolyModel):
    """A Client or the website"""
    creation_time = db.DateTimeProperty(auto_now_add = True, indexed = False)
    email         = db.StringProperty  (indexed=True)

    merchant = MemcacheReferenceProperty(db.Model, collection_name = "stores")
    # Store properties
    name    = db.StringProperty( indexed = False )
    url     = db.LinkProperty  ( indexed = True )
    domain  = db.LinkProperty  ( indexed = True )

    def __init__(self, *args, **kwargs):
        self._memcache_key = hashlib.md5(kwargs['email']).hexdigest() if 'email' in kwargs else None 
        super(Client, self).__init__(*args, **kwargs)
    
    @staticmethod
    def _get_from_datastore(google_user):
        """Datastore retrieval using memcache_key"""
        return db.Query(Client).filter('uuid =', google_user).get()
    
    @staticmethod
    def create(url, request_handler, user):
        """ Creates a Store (Client). 
            This process requires a user (merchant) to be associated with the
            client. Code must supply a user object for Client to be created.
        """

        uuid = hashlib.md5(url).hexdigest()

        if not user:
            raise ValueError ("User is missing")
        
        try:
            user_name = user.full_name
            user_email = user.emails[0] # emails is a back-reference
        except AttributeError, e:
            msg = "User supplied must have at least name and one email address"
            logging.error (msg, exc_info=True)
            raise AttributeError (msg) # can't really skip that

        # Now, make the store
        client = Client(
            key_name=uuid,
            uuid=uuid,
            name=user_name,
            email=user_email,
            url=url,
            domain=url, # I really don't see the difference.
            merchant=user
        )
        client.put()

        return client

    @staticmethod
    def get_or_create (url, request_handler=None, user=None):
        client = Client.get_by_url(url)
        if not client:
            client = ClientShopify.create( 
                url,
                request_handler,
                user
            )
        return client

    @classmethod
    def get_by_url (cls, url):
        res = cls.get(hashlib.md5(url).hexdigest()) # wild try w/ memcache?
        if res:
            return res
        # memcache miss?
        res = db.Query(cls).filter('url =', url).get()
        if res:
            return res
        # domain is the less-authoritative field, but if we need to use it, we will
        return db.Query(cls).filter('domain =', url).get()
    
# Accessors
def get_client_by_email( email ):
    client = Client.get(hashlib.md5(email).hexdigest())
    if client:
        return client
    return Client.all().filter( 'email =', email ).get()

def get_client_by_uuid( uuid ):
    return Client.all().filter( 'uuid =', uuid ).get()
