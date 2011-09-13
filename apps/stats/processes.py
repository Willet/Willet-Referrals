#!/usr/bin/env python

"""
Processes for Stats
"""
__all__ = [
    'Client'
]
import hashlib, logging, urllib, urllib2, uuid

from datetime import datetime
from django.utils import simplejson as json

from google.appengine.api import memcache, taskqueue, urlfetch

from apps.client.models import Client
from apps.stats.models import *
from apps.app.models import App, ShareCounter, get_app_by_id
from apps.link.models import Link, LinkCounter
from apps.user.models import User

from util.consts import *
from util.emails import Email
from util.helpers import *
from util.urihandler import URIHandler

class UpdateCounts(URIHandler):
    def get( self ): 
        stats = Stats.get_stats()
        stats.total_clients    = Client.all().count()
        stats.total_apps       = App.all().count()
        stats.total_links      = Link.all().count()
        stats.total_users      = User.all().count()
        stats.put()

class UpdateTweets(URIHandler):
    def get( self ):
        shares = ShareCounter.all()
        total  = 0
        for s in shares:
            total += s.count

        stats = Stats.get_stats()
        stats.total_tweets = total
        stats.put()

class UpdateClicks(URIHandler):
    def get( self ):
        links = LinkCounter.all()
        total  = 0
        for l in links:
            total += l.count

        stats = Stats.get_stats()
        stats.total_clicks = total
        stats.put()
