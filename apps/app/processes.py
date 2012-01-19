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

