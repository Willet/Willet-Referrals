#!/usr/bin/env python

# Feedback model
# stores text from giving us feedback via site.

import logging
from google.appengine.api import memcache
from google.appengine.ext import db

from util.model import Model

class Feedback(Model):
    """Model storing the data for a client's sharing campaign"""
    created = db.DateTimeProperty(auto_now_add=True)
    message = db.StringProperty(multiline=True)
    client  = db.ReferenceProperty( db.Model, collection_name = 'feedback' )
    
    def __init__(self, *args, **kwargs):
        self._memcache_key = kwargs['created'] if 'created' in kwargs else None 
        super(Feedback, self).__init__(*args, **kwargs)
    
    @staticmethod
    def _get_from_datastore(created):
        """Datastore retrieval using memcache_key"""
        return db.Query(Feedback).filter('created =', created).get()

