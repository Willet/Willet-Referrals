#!/usr/bin/env python

__author__ = "Willet, Inc."
__copyright__ = "Copyright 2011, Willet, Inc"

from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

from apps.app.models import * 
from apps.client.models import Client

from util.helpers import *
from util.urihandler import URIHandler
from util.consts import *

# The "Dos" --------------------------------------------------------------------
class DoDeleteApp( URIHandler ):
    def post( self ):
        client = self.get_client()
        app_uuid = self.request.get( 'app_uuid' )
        
        logging.info('app id: %s' % app_uuid)
        app = App.get_by_uuid(app_uuid)
        if app.client.key() == client.key():
            logging.info('deelting')
            app.delete()
        
        self.redirect( '/client/account' )

