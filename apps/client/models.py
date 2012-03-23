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

    def __init__(self, *args, **kwargs):
        self._memcache_key = hashlib.md5(kwargs['email']).hexdigest() if 'email' in kwargs else None 
        super(Client, self).__init__(*args, **kwargs)
    
    @staticmethod
    def _get_from_datastore(google_user):
        """Datastore retrieval using memcache_key"""
        return db.Query(Client).filter('uuid =', google_user).get()
        
# Accessors
def get_client_by_email( email ):
    client = Client.get(hashlib.md5(email).hexdigest())
    if client:
        return client
    return Client.all().filter( 'email =', email ).get()

def get_client_by_uuid( uuid ):
    return Client.all().filter( 'uuid =', uuid ).get()
