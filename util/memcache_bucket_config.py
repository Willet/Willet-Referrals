#!/usr/bin/env python

import random
import logging

from google.appengine.ext    import db

from util.model import Model

class MemcacheBucketConfig(Model):
    """Used so we can dynamically scale the number of memcache buckets"""
    name = db.StringProperty(indexed = True)
    count = db.IntegerProperty(default = 20)
    _memcache_key_name = 'name'

    def __init__(self, *args, **kwargs):
        self._memcache_key = kwargs[self._memcache_key_name] if self._memcache_key_name in kwargs else None 
        super(MemcacheBucketConfig, self).__init__(*args, **kwargs)

    def get_bucket(self, number):
        return '%s:%s' % (self.name, number)

    def get_random_bucket(self):
        bucket = random.randint(0, self.count)
        return self.get_bucket(bucket) 

    def decrement_count(self):
        if self.count == 0:
            logging.error('trying to decrement count for %s lower than 0' % 
                    self.name)
        else:
            self.count -= 1
            self.put()

    def increment_count(self):
        self.count += 1
        self.put()

    @staticmethod
    def create(name):
        mbc = MemcacheBucketConfig(name=name)
        if mbc:
            mbc.put()
        return mbc

    @staticmethod
    def get_or_create(name):
        mbc = MemcacheBucketConfig.get(name)
        if not mbc:
            # we are creating this MBC for the first time
            mbc = MemcacheBucketConfig.create(name)
        return mbc
    
    @classmethod
    def _get_from_datastore(cls, name):
        """Datastore retrieval using memcache_key"""
        return cls.all().filter('%s =' % cls._memcache_key_name, name).get()

