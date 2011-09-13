#!/usr/bin/env python

import uuid

from google.appengine.ext import db

from util.model import Model

class Stats(Model):
    uuid            = db.StringProperty()
    landing         = db.TextProperty()
    total_tweets    = db.IntegerProperty( default = 0 )
    total_clicks    = db.IntegerProperty( default = 0 )
    total_links     = db.IntegerProperty( default = 0 )
    total_apps      = db.IntegerProperty( default = 0 )
    total_clients   = db.IntegerProperty( default = 0 )
    total_users     = db.IntegerProperty( default = 0 )
    
    def __init__(self, *args, **kwargs):
        self._memcache_key = kwargs['uuid'] if 'uuid' in kwargs else None 
        super(Stats, self).__init__(*args, **kwargs)
    
    @staticmethod
    def _get_from_datastore(uuid):
        """Datastore retrieval using memcache_key"""
        return db.Query(Stats).filter('uuid =', uuid).get()
    
    @staticmethod
    def get_stats():
        stats = Stats.all().get()
        if stats == None:
            stats = Stats(uuid=uuid.uuid4().hex)
            stats.put()
        return stats

