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
from models.model         import Model
from util.helpers         import *

class UserAnalytics(Model):
    """
    For a given scope, the users analytics are calculated as a
    snapshot of that scope's activities
    """
    uuid            = db.StringProperty(indexed = True)
    creation_time   = db.DateTimeProperty(auto_now_add = True)

    # user this is for
    user            = db.ReferenceProperty(db.Model, collection_name='users_analytics')
    
    # the campaign for which these stats are being calcualted
    campaign        = db.ReferenceProperty(db.Model, collection_name='user_analytics')
    
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
    profit = db.FloatProperty(default = 0)

    # snapshot of the users reach on this scope for this service
    reach = db.IntegerProperty(default = 0)

    def __init__(self, *args, **kwargs):
        self._memcache_key = kwargs['uuid'] if 'uuid' in kwargs else None 
        super(ServiceStats, self).__init__(*args, **kwargs)

