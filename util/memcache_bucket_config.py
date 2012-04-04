#!/usr/bin/env python

import random
import logging

from google.appengine.ext import db
from google.appengine.api import memcache
from google.appengine.datastore import entity_pb
from google.appengine.ext import deferred

from apps.user.models import *
from util.model import Model
from util.consts import MEMCACHE_TIMEOUT
from util.consts import MEMCACHE_BUCKET_COUNTS

class MemcacheBucketConfig(Model):
    """Used so we can dynamically scale the number of memcache buckets"""
    name = db.StringProperty(indexed = True)
    count = db.IntegerProperty(default = 20)
    _memcache_key_name = 'name'
    
    memcache_fields = ['id', 'name']

    def __init__(self, *args, **kwargs):
        self._memcache_key = kwargs[self._memcache_key_name] if self._memcache_key_name in kwargs else None 
        super(MemcacheBucketConfig, self).__init__(*args, **kwargs)

    def _validate_self(self):
        return True

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

    def put_later(self, entity):
        """Will put this entity in a bucket!"""
        key = entity.get_key()

        memcache.set(key, db.model_to_protobuf(entity).Encode(), time=MEMCACHE_TIMEOUT)

        bucket = self.get_random_bucket()
        #logging.info('mbc: %s' % self.name)
        #logging.info('bucket: %s' % bucket)

        list_identities = memcache.get(bucket) or []
        list_identities.append(key)

        #logging.info('bucket length: %d/%d' % (len(list_identities), self.count))
        if len(list_identities) > self.count:
            memcache.set(bucket, [], time=MEMCACHE_TIMEOUT)
            #logging.warn('bucket overflowing, persisting!')
            deferred.defer(batch_put, self.name, bucket, list_identities, _queue='slow-deferred')
        else:
            memcache.set(bucket, list_identities, time=MEMCACHE_TIMEOUT)

        #logging.info('put_later: %s' % key)

    @staticmethod
    def create(name, count=None):
        if not count:
            if name in MEMCACHE_BUCKET_COUNTS:
                count = MEMCACHE_BUCKET_COUNTS[name]
            else:
                count = MEMCACHE_BUCKET_COUNTS['default']
        mbc = MemcacheBucketConfig(name=name, count=count)
        if mbc:
            mbc.put()
        return mbc

    @staticmethod
    def get_or_create(name, count=None):
        mbc = MemcacheBucketConfig.get(name)
        if not mbc:
            # we are creating this MBC for the first time
            mbc = MemcacheBucketConfig.create(name, count)
        return mbc
    
    @classmethod
    def _get_from_datastore(cls, name):
        """Datastore retrieval using memcache_key"""
        return cls.all().filter('%s =' % cls._memcache_key_name, name).get()

def batch_put(mbc_name, bucket_key, list_keys, decrementing=False):
    # TODO - make classmethod of MemcacheBucketConfig

    logging.info("Batch putting %s to memcache: %s" % (mbc_name, list_keys))
    mbc = MemcacheBucketConfig.get_or_create(mbc_name)
    entities_to_put = []
    had_error = False
    object_dict = memcache.get_multi(list_keys)
    for key in list_keys:
        data = object_dict.get(key)
        try:
            entity = db.model_from_protobuf(entity_pb.EntityProto(data))
            if entity:
                entities_to_put.append(entity)
        except AssertionError, e:
            old_key = mbc.get_bucket(mbc.count)
            if bucket_key != old_key and not decrementing and not had_error:
                old_count = mbc.count
                mbc.decrement_count()
                logging.warn(
                    'encounted error, going to decrement buckets from %s to %s' 
                    % (old_count, mbc.count), exc_info=True)

                last_keys = memcache.get(old_key) or []
                memcache.set(old_key, [], time=MEMCACHE_TIMEOUT)
                deferred.defer(batch_put, mbc_name, old_key, last_keys, 
                        decrementing=True, _queue='slow-deferred')
                had_error = True
        except Exception, e:
            logging.error('error getting object: %s' % e, exc_info=True)

    try:
        #def txn():
        db.put_async(entities_to_put)
        #db.run_in_transaction(txn)
        for entity in entities_to_put:
            if entity.key():
                memcache_key = entity.get_key()
                memcache.set(memcache_key, 
                        db.model_to_protobuf(entity).Encode(), 
                        time=MEMCACHE_TIMEOUT)
    except Exception,e:
        logging.error('Error putting %s: %s' % (entities_to_put, e), exc_info=True)

    if decrementing:
        logging.warn('decremented mbc `%s` to %d and removed %s' % (
            mbc.name, mbc.count, bucket_key))

