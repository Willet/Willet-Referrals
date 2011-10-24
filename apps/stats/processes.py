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

from apps.stats.models import *
from apps.action.models import ClickAction
from apps.action.models import VoteAction
from apps.buttons.actions import WantAction
from apps.sibt.models import SIBTInstance

from util.consts import *
from util.helpers import *
from util.urihandler import URIHandler

class UpdateCounts(URIHandler):
    def get( self ): 
        stats = Stats.get_stats()
        stats.total_instances  = SIBTInstance.all().count()
        stats.total_clicks     = ClickAction.all().count()
        stats.total_votes      = VoteAction.all().count()
        stats.total_wants      = WantAction.all().count()
        stats.put()
