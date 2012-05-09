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

from apps.app.models import *
from apps.app.shopify.models import *
from apps.sibt.shopify.models import *
from apps.buttons.shopify.models import *

from util.consts import MEMCACHE_TIMEOUT

actions_to_count = [
    'ScriptLoadAction',

    'SIBTUserClickedTopBarAsk',
    'SIBTUserClickedButtonAsk',
    'SIBTUserClickedOverlayAsk',
    'SIBTUserClickedTabAsk',
    'SIBTAskUserClickedShare',
    'SIBTVisitLength',

    'SIBTShowingTopBarAsk',
    'SIBTShowingButton',
    'SIBTShowingAskIframe',
    'SIBTShowingResults',
    'SIBTShowingResultsToAsker',

    'SIBTAskUserClosedIframe',
    'SIBTAskUserClickedShare',

    'SIBTInstanceCreated',
    'SIBTVoteAction',
    'SIBTUserAction',
    'SIBTFBConnected',

    'SIBTUserClosedTopBar',
    'SIBTUserReOpenedTopBar',
    'SIBTAskIframeCancelled',
    'SIBTNoConnectFBDialog',
    'SIBTNoConnectFBCancelled',
    'SIBTConnectFBDialog',
    'SIBTConnectFBCancelled',
    'SIBTFriendChoosingCancelled'
]

# removing duplicates for the lazy
actions_to_count = list(set(actions_to_count))

actions_to_average = [
    'SIBTVisitLength',
]
# removing duplicates for the lazy
actions_to_average = list(set(actions_to_average))


class AnalyticsTimeSlice(db.Expando):
    start = db.DateTimeProperty()
    end = db.DateTimeProperty()

    def increment(self, attr, new):
        old = 0
        if hasattr(self, attr):
            old = getattr(self, attr)
        new += old
        setattr(self, attr, new)

    def get_attr(self, attr):
        value = 0
        if hasattr(self, attr):
            value = getattr(self, attr)
        return value

    def default(self, action):
        setattr(self, action, 0)

    def __str__(self):
        return '%s-%s' % (self.__class__.__name__, self.start)


class AppAnalyticsTimeSlice(AnalyticsTimeSlice):
    """Generic Time Slice
    @TODO
        MEMCACHE IS DISABLED FOR TESTING
    """
    app_ = db.ReferenceProperty(App)

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
                db.put(self)
            except datastore_errors.Timeout:
                thread.sleep(timeout_ms)
                timeout_ms *= 2
            else:
                break
        # Memcache *after* model is given datastore key
        #if self.key():
        #    logging.debug('setting new memcache entity: %s' % key)
        #    memcache.set(key, db.model_to_protobuf(self).Encode(),
        #            time=MEMCACHE_TIMEOUT)

        return True

    def get_key(self):
        return self.__class__.build_key(self.app_, self.start)
        #return '%s:%s' % (self.__class__.__name__, self.start)

    @classmethod
    def build_key(cls, app_, start):
        return '%s:%s:%s' % (cls.__name__, app_.uuid, start)

    @classmethod
    def _get_from_datastore(cls, app_, start):
        return cls.all()\
                .filter('app_ =', app_)\
                .filter('start =', start)\
                .get()

    @classmethod
    def get(cls, app_, start):
        """Checks memcache for model before hitting database
        Each class must have a staticmethod get_from_datastore
        TODO(barbara): Enforce the above statement!!!
        Also, should it be: get_from_datastore OR _get_from_datastore?
        """
        return cls._get_from_datastore(app_, start)


class AppAnalyticsHourSlice(AppAnalyticsTimeSlice):
    """A TimeSlice is a period of time with a start and end datetime that
    reflects the start and the end of the period.

    We count the number of each action for this time slice.

    The exact properties of a time slice are determined at run time
    """

    @classmethod
    def create(cls, app_, start, put=True):
        """Let's create a TimeSlice!
        Start is the datetime when this timeslice starts!
        """
        end = start + datetime.timedelta(hours=1)
        dr = [start, end]
        ahs = cls(app_=app_, start=start, end=end, date_range=dr)
        if put:
            ahs.put()
        return ahs

    @classmethod
    def get_or_create(cls, app_, start, put=True):
        ahs = cls.get(app_, start)
        created = False
        if not ahs:
            ahs = cls.create(app_=app_, start=start, put=put)
            created = True

        return ahs, created


class AppAnalyticsDaySlice(AppAnalyticsTimeSlice):
    @classmethod
    def create(cls, app_, start, put=True):
        end = start + datetime.timedelta(hours=24)
        ahs = cls(app_=app_, start=start, end=end)
        if put:
            ahs.put()
        return ahs

    @classmethod
    def get_or_create(cls, app_, start, put=True):
        logging.info('looking up %s\n%s\n%s' % (cls, app_, start))
        ahs = cls.get(app_, start)
        logging.info('got %s' % ahs)
        created = False
        if not ahs:
            ahs = cls.create(app_=app_, start=start, put=put)
            logging.info('created')
            created = True

        return ahs, created


class GlobalAnalyticsTimeSlice(AnalyticsTimeSlice):
    def put(self):
        """Stores model instance in memcache and database"""
        key = self.get_key()
        timeout_ms = 100
        while True:
            try:
                db.put(self)
            except datastore_errors.Timeout:
                thread.sleep(timeout_ms)
                timeout_ms *= 2
            else:
                break
        #if self.key():
        #    memcache.set(key, db.model_to_protobuf(self).Encode(),
        #            time=MEMCACHE_TIMEOUT)

        return True

    def get_key(self):
        return self.__class__.build_key(self.start)

    @classmethod
    def build_key(cls, start):
        return '%s:%s' % (cls.__name__, start)

    @classmethod
    def _get_from_datastore(cls, start):
        return cls.all().filter('start =', start).get()

    @classmethod
    def get(cls, start):
        """Checks memcache for model before hitting database
        Each class must have a staticmethod get_from_datastore
        TODO(barbara): Enforce the above statement!!!
        Also, should it be: get_from_datastore OR _get_from_datastore?
        """
        return cls._get_from_datastore(start)


class GlobalAnalyticsHourSlice(GlobalAnalyticsTimeSlice):
    @classmethod
    def create(cls, start, put=True):
        end = start + datetime.timedelta(hours=1)
        dr = [start, end]
        gats = cls(start=start, end=end, date_range=dr)
        if put:
            gats.put()
        return gats

    @classmethod
    def get_or_create(cls, start, put=True):
        gats = cls.get(start)
        created = False
        if not gats:
            gats = cls.create(start, put=put)
            created = True
        return gats, created


class GlobalAnalyticsDaySlice(GlobalAnalyticsTimeSlice):
    @classmethod
    def create(cls, start, put=True):
        end = start + datetime.timedelta(hours=24)
        dr = [start, end]
        gats = cls(start=start, end=end, date_range=dr)
        if put:
            gats.put()
        return gats

    @classmethod
    def get_or_create(cls, start, put=True):
        gats = cls.get(start)
        created = False
        if not gats:
            gats = cls.create(start, put=put)
            created = True
        return gats, created
