#!/usr/bin/env python

import uuid

from google.appengine.ext import db

from util.model import Model

class Stats(Model):
    uuid            = db.StringProperty()
    total_instances = db.IntegerProperty( default = 0 )
    total_clicks    = db.IntegerProperty( default = 0 )
    total_votes     = db.IntegerProperty( default = 0 )
    total_wants     = db.IntegerProperty( default = 0 )
    
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

