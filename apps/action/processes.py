#!/usr/bin/env python

__author__ = "Barbara Macdonald"
__copyright__ = "Copyright 2012, Barbara"

import logging

from apps.action.models import ShowAction
from apps.action.models import UserAction
from apps.user.models import User
from apps.app.models import App

from util.urihandler import URIHandler

class TrackShowAction(URIHandler):
    def post(self):
        """Javascript can track generic Show Actions."""

        '''
        try:
            user = User.get(self.request.get('user'))
            app = App.get(self.request.get('app'))
            what = self.request.get('evnt')

            action = ShowAction.create(user, app, what)
            logging.info('Created action %s' % action)
        except Exception, err:
            logging.error('There was an error storing the action: %s' % err,
                          exc_info=True)
        '''
        return  # Action logging is disabled 2012-05-24


class TrackUserAction(URIHandler):
    def post(self):
        """Javascript can track generic user Actions."""

        '''
        try:
            user = User.get(self.request.get('user'))
            app = App.get(self.request.get('app'))
            what = self.request.get('evnt')

            action = UserAction.create(user, app, what)
            logging.info('Created action %s' % action)
        except Exception, err:
            logging.error('There was an error storing the action: %s' % err,
                          exc_info=True)
        '''
        return  # Action logging is disabled 2012-05-24