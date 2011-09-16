#!/usr/bin/env python

"""
User Analytics Processes
"""
import hashlib, logging, urllib, urllib2, uuid

from datetime import datetime
from django.utils import simplejson as json

from google.appengine.api import memcache, taskqueue, urlfetch
from google.appengine.ext import db, webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

from apps.user_analytics.models import *

from apps.user.models import *


class TriggerUserAnalytics(webapp.RequestHandler):
    """
    Adds a task for each user active in a campaign
    """
    def get(self):
        scope = self.request.get('scope', 'day')
        users = User.all()
        for u in users:
            taskqueue.add(url = '/user_analytics/compute',
                params = {
                    'user_key': u.key(),
                    'scope': scope
                }
            )
        logging.info('triggered analytics for %d users' % users.count())
        return

class ComputeUserAnalytics(webapp.RequestHandler):
    """Computes the analytics for this user for this scope"""
    def post(self):
        key = self.request.get('user_key', '')
        scope = self.request.get('scope', 'day')

        if key == '':
            logging.error('called computeUserAnalytic with no key')
        else:
            user = User.get(key)
            if user:
                logging.info("computing analytics for user %s" % key)
                user.compute_analytics(scope)
            else:
                logging.error('called computeUserAnalytics with bad key %s' % key)
        return


