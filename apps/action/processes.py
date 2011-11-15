#!/usr/bin/env python

__author__      = "Barbara Macdonald"
__copyright__   = "Copyright 2011, Barbara"

import logging
import datetime

#from django.utils import simplejson as json
#from google.appengine.api import urlfetch
from google.appengine.ext import webapp
#from google.appengine.ext.webapp import template

from apps.action.models import ShowAction 
from apps.action.models import UserAction 
from apps.user.models import User
from apps.app.models import App

from util.consts import *

class TrackShowAction(webapp.RequestHandler):
    def post(self):
        """Javascript can track generic Show Actions"""
        try:
            user = User.get(self.request.get('user')) if self.request.get('user') else None
            app = App.get(self.request.get('app')) if self.request.get('app') else None
            what = self.request.get('what')

            action = ShowAction.create(user, app, what)
            logging.info('Created action %s' % action)
        except Exception,e:
            logging.error('There was an error storing the action: %s' % e, 
                    exc_info=True)

class TrackUserAction(webapp.RequestHandler):
    def post(self):
        """Javascript can track generic user Actions"""
        try:
            user = User.get(self.request.get('user')) if self.request.get('user') else None
            app = App.get(self.request.get('app')) if self.request.get('app') else None
            what = self.request.get('what')

            action = UserAction.create(user, app, what)
            logging.info('Created action %s' % action)
        except Exception,e:
            logging.error('There was an error storing the action: %s' % e, 
                    exc_info=True)

