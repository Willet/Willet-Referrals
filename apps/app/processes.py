#!/usr/bin/env python

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc"

from google.appengine.api import memcache, taskqueue, urlfetch
from google.appengine.ext import webapp

from apps.app.models      import App, ShareCounter
from apps.user.models     import * 
from util.consts          import *
from util.helpers         import *
from util.urihandler      import URIHandler


class BatchRequest(URIHandler):
    """ EXPERIMENTAL: Start a batch request of a class method, which will run
    for every app of app_cls in the db """
    def get(self):
        self.post()

    def post(self):
        """ Expected inputs:
            - batch_size: (int) 0 - 1000, 100 is good in general
            - offset: (int) database offset
            - app_cls: App class
            - target_version: (Optional)
            - method: method to call on app_cls
            - params: JSON-encoded parameters to send to method
        """
        batch_size = self.request.get('batch_size')
        offset = self.request.get('offset')
        app_cls = self.request.get('app_cls')
        target_version = self.request.get('target_version')
        method = self.request.get('method')
        params = json.loads( self.request.get('params'))

        if not batch_size or not (offset >= 0) or not app_cls:
            self.error(400) # Bad Request
            return

        apps = db.Query(App).filter('class = ', app_cls).fetch(limit=batch_size, offset=offset)

        # Check that method is safe and callable
        if method:
            if method[0] == '_':
                self.error(403) # Access Denied
                return
            try:
                if not hasattr(getattr(app_cls, method), '__call__'):
                    raise AttributeError
            except AttributeError:
                self.error(400) # Bad Request

        # If reached batch size, start another batch at the next offset
        if len(apps) == batch_size:
            p = {
                'batch_size':       batch_size,
                'offset':           offset + batch,
                'app_cls':          app_cls,
                'target_version':   target_version,
                'method':           method,
                'params':           self.request.get('params')
            }
            taskqueue.add(url=url('BatchRequest'), params=p)

        # For each app, try to create an email & send it
        for app in all_apps:
            try:
                # Check version
                if target_version >= 0 and app.version != target_version:
                    # Wrong version, skip this one
                    continue
                getattr(app, method)()
            except Exception, e:
                logging.warn('%s.%s.%s() failed because %r' % (app.__class__.__module__, app.__class__.__name__, method, e))
                continue


class AppClicksCounter(URIHandler):
    def post( self ): 
        app = App.get_by_uuid(self.request.get('app_uuid'))
        
        app.cached_clicks_count = 0
        if hasattr( app, 'links_' ):
            for l in app.links_:
                app.cached_clicks_count += l.count_clicks()

        app.put()

