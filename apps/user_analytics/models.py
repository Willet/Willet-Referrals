#!/usr/bin/env python
"""
User Analytics are calculated once per day for each user
Tracks shares, click throughs, conversions, and profit
"""

import logging
import sys

from django.utils import simplejson

from datetime import datetime
from decimal  import *
from time import time
from hmac import new as hmac
from hashlib import sha1
from traceback import print_tb

from google.appengine.api import memcache
from google.appengine.api import urlfetch
from google.appengine.api import taskqueue
from google.appengine.ext import db

from util.model         import Model
from util.helpers         import *

class UserAnalytics(Model):
    """
    For a given scope, the users analytics are calculated as a
    snapshot of that scope's activities
    """
    uuid = db.StringProperty(indexed = True)
    creation_time = db.DateTimeProperty(auto_now_add = True)
    period_start = db.DateTimeProperty()
    # user this is for
    user = db.ReferenceProperty(db.Model, collection_name='users_analytics')
    
    # the campaign for which these stats are being calcualted
    campaign = db.ReferenceProperty(db.Model, collection_name='campaign_users_analytics')
    
    # the 'scope' of this analytics
    # either 'day, week, month, year'
    scope = db.StringProperty(indexed = True)

    def __init__(self, *args, **kwargs):
        self._memcache_key = kwargs['uuid'] if 'uuid' in kwargs else None 
        super(UserAnalytics, self).__init__(*args, **kwargs)
    

class ServiceStats(Model):
    user_analytics = db.ReferenceProperty(UserAnalytics, collection_name='stats')
    
    # name of the service:
    # ex: 'facebook', 'linkedin', 'twitter', 'total (all of the above)'
    service = db.StringProperty()

    # basically number of links for this user for this scope 
    shares = db.IntegerProperty(default=0)

    # number of clicks
    clicks = db.IntegerProperty(default = 0)

    # number of conversions
    conversions = db.IntegerProperty(default = 0)

    # total dollay value of sales for this scope 
    profit = db.FloatProperty(default = float(0))

    # snapshot of the users reach on this scope for this service
    reach = db.IntegerProperty(default = 0)

    def __init__(self, *args, **kwargs):
        self._memcache_key = kwargs['uuid'] if 'uuid' in kwargs else None 
        super(ServiceStats, self).__init__(*args, **kwargs)

def get_or_create_ua(user, campaign, scope, period_start):
    ua = UserAnalytics.all()\
            .filter('user =', user)\
            .filter('campaign =', campaign)\
            .filter('scope =', scope)\
            .filter('period_start =', period_start).get()
    
    if ua == None:
        ua = UserAnalytics(
            user = user,
            campaign = campaign,
            scope = scope,
            period_start = period_start
        )
        ua.put()
    return ua

def get_or_create_ss(ua, service):
    """ attempts to get or create a ss"""
    ss = ServiceStats.all()\
            .filter('user_analytics =', ua)\
            .filter('service =', service).get()
    if ss == None:
        ss = ServiceStats(
            user_analytics = ua,
            service = service
        )
        ss.put()

    return ss

