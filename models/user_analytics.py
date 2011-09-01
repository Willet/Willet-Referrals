#!/usr/bin/env python
"""
User Analytics are calculated once per day for each user
Tracks referrals, click throughs, conversions, and profit
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
from models.user          import User
from models.oauth         import OAuthClient
from util.emails          import Email
from util.helpers         import *
from util import oauth2 as oauth

class UserAnalytics(Model):
    uuid            = db.StringProperty(indexed = True)
    creation_time   = db.DateTimeProperty(auto_now_add = True)

    # user this is for
    user            = db.ReferenceProperty(db.Model, collection_name='users_analytics')

class ServiceStats(Model):
    user_analytics = db.ReferenceProperty(UserAnalytics, collection_name='stats')
    
    # name of the service:
    # ex: 'facebook', 'linkedin', 'twitter'
    service = db.StringProperty()

    # basically number of links for this user for this day
    shares = db.IntegerProperty()

    # number of clicks
    clicks = db.IntegerProperty()

    # number of conversions
    conversions = db.IntegerProperty()

    # total dollay value of sales for this day
    profit = db.FloatProperty()

    # snapshot of the users reach on this day for this service
    reach = db.IntegerProperty()
