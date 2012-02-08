#!/usr/bin/env python

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc"

import re, urllib

from django.utils import simplejson as json
from google.appengine.api import urlfetch, memcache
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app
from time import time

from apps.app.models import * 
from apps.link.models import Link, get_link_by_willt_code
from apps.user.models import get_user_by_cookie, User
from apps.client.models import Client
from apps.order.models import *

from util.gaesessions import get_current_session
from util.helpers     import *
from util.urihandler  import URIHandler
from util.consts      import *

# The "Dos" --------------------------------------------------------------------
class DoDeleteApp( URIHandler ):
    def post( self ):
        client   = self.get_client()
        app_uuid = self.request.get( 'app_uuid' )
        
        logging.info('app id: %s' % app_uuid)
        app = get_app_by_id( app_uuid )
        if app.client.key() == client.key():
            logging.info('deelting')
            app.delete()
        
        self.redirect( '/client/account' )

