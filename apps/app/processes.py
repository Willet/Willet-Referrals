#!/usr/bin/env python

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc"

from google.appengine.api import memcache, taskqueue, urlfetch
from google.appengine.ext import webapp

from apps.app.models      import App, ShareCounter, get_app_by_id
from apps.user.models     import * 
from util.consts          import *
from util.helpers         import *
from util.urihandler      import URIHandler

class AppClicksCounter( webapp.RequestHandler ):
    def post( self ): 
        app = get_app_by_id( self.request.get('app_uuid') )
        
        app.cached_clicks_count = 0
        if hasattr( app, 'links_' ):
            for l in app.links_:
                app.cached_clicks_count += l.count_clicks()

        app.put()

class TriggerAppAnalytics(webapp.RequestHandler):
    def get(self):
        scope = self.request.get('scope', 'week')
        apps  = App.all()
        for c in apps:
            taskqueue.add( url    = '/computeAppAnalytics',
                           params = { 'ca_key': c.key(), 
                                      'scope'  : scope, } )

class ComputeAppAnalytics(webapp.RequestHandler):
    def post(self):
        rq_vars = get_request_variables(['ca_key', 'scope'], self)
        ca = db.get(rq_vars['ca_key'])
        ca.compute_analytics(rq_vars['scope'])
