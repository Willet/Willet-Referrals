#!/usr/bin/env python

__author__ = "Willet, Inc."
__copyright__ = "Copyright 2011, Willet, Inc"

from google.appengine.api import memcache, taskqueue, urlfetch
from google.appengine.ext import webapp
import django.utils.simplejson as json

from apps.app.models import App, ShareCounter
from apps.user.models import * 
from util.consts import *
from util.helpers import *
from util.urihandler import URIHandler


class BatchRequest(URIHandler):
    """ I-CAN'T-BELIEVE-IT'S-EXPERIMENTAL: Start a batch request of a class
        method, which will run for every app of app_cls in the db """
    def get(self):
        self.post()

    def post(self):
        """ Expected inputs:
            - app_cls    : App class
            - method     : method to call on app_cls
            - batch_size*: 0 - 1000, 100 is good in general
            - offset    *: database offset
            - params    *: JSON-encoded parameters to send to method
            - criteria  *: JSON-encoded matching criteria
                           to filter (equality only)
                           NOTE: the criteria need to be indexed!

            *Optional
        """
        app_cls        = self.request.get('app_cls')
        method         = self.request.get('method')

        batch_size     = int(self.request.get('batch_size', 100))
        offset         = int(self.request.get('offset', 0))
        params         = json.loads(self.request.get('params', "{}"))
        criteria       = json.loads(self.request.get('criteria', "{}"))

        # Convert JSON keys from unicode to strings
        # Python 2.5 doesn't like this, but it will work in 2.7
        # We do this because we will be using the keys as kwargs
        converted_params = dict( (key.encode('utf-8'), value) for key, value in params.iteritems() )

        filter_obj = db.Query(App).filter('class = ', app_cls)
        for ukey, value in criteria.iteritems():
            key = " %s =" % ukey.encode('utf-8')
            filter_obj.filter(key, value)

        apps = filter_obj.fetch(limit=batch_size, offset=offset)

        # Check that method is safe and callable
        if method:
            if method[0] == '_':
                self.error(403) # Access Denied, Private method
                return
            try:
                if not hasattr(getattr(app_cls, method), '__call__'):
                    raise AttributeError
            except AttributeError:
                self.error(400) # Bad Request

        # If reached batch size, start another batch at the next offset
        if len(apps) == batch_size:
            p = {
                'batch_size': batch_size,
                'offset'    : offset + batch_size,
                'app_cls'   : app_cls,
                'method'    : method,
                'params'    : self.request.get('params'),
                'criteria'  : self.request.get('criteria')
            }
            taskqueue.add(url=url('BatchRequest'), params=p)

        # For each app, try to create an email & send it
        for app in apps:
            try:
                getattr(app, method)(**converted_params)
            except Exception, e:
                logging.warn('%s.%s.%s() failed because %r' % (app.__class__.__module__,
                                                               app.__class__.__name__,
                                                               method,
                                                               e))
                continue


class AppClicksCounter(URIHandler):
    def post(self): 
        app = App.get_by_uuid(self.request.get('app_uuid'))

        app.cached_clicks_count = 0
        if hasattr(app, 'links_'):
            for l in app.links_:
                app.cached_clicks_count += l.count_clicks()

        app.put()

