#!/usr/bin/env python

"""
For details on the structure used here please refer to:
    http://code.google.com/appengine/articles/mr/mapper.html
"""

import datetime
import logging

from google.appengine.api import memcache
from google.appengine.api import datastore_errors
from google.appengine.datastore import entity_pb
from google.appengine.ext import db

from util.consts import MEMCACHE_TIMEOUT

#from apps.action.models import *

#from apps.sibt.actions import *

actions_to_count = [
    #'SIBTAskUserClickedEditMotivation',

    # top bar actions
    'SIBTUserClickedTopBarAsk',
    'SIBTShowingTopBarAsk',

    # button actions
    'SIBTUserClickedButtonAsk',
    'SIBTShowingButton',

    # ask actions
    'SIBTShowingAskIframe',
    'SIBTAskUserClosedIframe',
    'SIBTAskUserClickedShare',
    'SIBTInstanceCreated',
]

class AnalyticsTimeSlice(db.Expando):
    """Generic Time Slice"""
    start = db.DateTimeProperty()
    end = db.DateTiemProperty()

    def get_key(self):
        return '%s:%s' % (self.__class__.__name__, self.start)

    def put(self):
        """Stores model instance in memcache and database"""
        key = self.get_key()
        logging.debug('Model::save(): Saving %s to memcache and datastore.' % 
                key)
        timeout_ms = 100
        while True:
            logging.debug('Model::save(): Trying %s.put, timeout_ms=%i.' % 
                    (self.__class__.__name__.lower(), timeout_ms))
            try:
                self.hardPut() # Will validate the instance.
            except datastore_errors.Timeout:
                thread.sleep(timeout_ms)
                timeout_ms *= 2
            else:
                break
        # Memcache *after* model is given datastore key
        if self.key():
            logging.debug('setting new memcache entity: %s' % key)
            memcache.set(key, db.model_to_protobuf(self).Encode(), 
                    time=MEMCACHE_TIMEOUT)
            
        return True

    @classmethod
    def get(cls, memcache_key):
        """Checks memcache for model before hitting database
        Each class must have a staticmethod get_from_datastore
        TODO(barbara): Enforce the above statement!!!
        Also, should it be: get_from_datastore OR _get_from_datastore?
        """
        key = cls.build_key(memcache_key)
        logging.debug('Model::get(): Pulling %s from memcache.' % key)
        data = memcache.get(key)
        if not data:
            logging.debug('%s::get(): %s not found in memcache, \
                    hitting datastore.' % (cls, key))
            entity = cls._get_from_datastore(memcache_key)
            if entity:
                logging.debug('setting new memcache entity: %s' % key)
                memcache.set(key, db.model_to_protobuf(entity).Encode(), 
                        time=MEMCACHE_TIMEOUT)
            return entity
        else:
            logging.debug('Model::get(): %s found in memcache!' % key)
            return db.model_from_protobuf(entity_pb.EntityProto(data))

class AnalyticsHourSlice(AnalyticsTimeSlice):
    """A TimeSlice is a period of time with a start and end datetime that 
    reflects the start and the end of the period.

    We count the number of each action for this time slice.

    The exact properties of a time slice are determined at run time
    """

    @classmethod
    def create(cls, start, put=True):
        """Let's create a TimeSlice!
        Start is the datetime when this timeslice starts!
        """
        end = start + datetime.timedelta(hours=1)
        ahs = cls(start=start, end=end)
        if put:
            ahs.put()
        return ahs

    @classmethod
    def get_or_create(cls, start):
        ahs = cls.get(start)
        created = False
        if not ahs:
            ahs = cls.create(start=start)
            created = True

        return ahs, created

class AnalyticsDaySlice(AnalyticsTimeSlice):
    @classmethod
    def create(cls, start, put=True):
        """Let's create a TimeSlice!
        Start is the datetime when this timeslice starts!
        """
        end = start + datetime.timedelta(hours=1)
        ahs = cls(start=start, end=end)
        if put:
            ahs.put()
        return ahs

    @classmethod
    def get_or_create(cls, hour):
        ahs = cls.get(hour)
        created = False
        if not ahs:
            ahs = cls.create(start=hour)
            created = True

        return ahs, created
