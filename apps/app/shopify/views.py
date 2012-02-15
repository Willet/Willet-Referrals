#!/usr/bin/env python

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc"

import re
import urllib

from django.utils               import simplejson as json
from google.appengine.api       import memcache
from google.appengine.api       import urlfetch
from google.appengine.ext       import webapp
from google.appengine.ext.webapp      import template
from google.appengine.ext.webapp.util import run_wsgi_app
from time                       import time

from apps.app.models            import * 
from apps.client.shopify.models import ClientShopify
from apps.link.models           import Link
from apps.user.models           import User
from apps.user.models           import get_or_create_user_by_cookie
from apps.user.models           import get_user_by_cookie

from apps.order.models          import *

from util.gaesessions           import get_current_session
from util.helpers               import *
from util.urihandler            import URIHandler
from util.consts                import *

# The "Shows" ------------------------------------------------------------------
class ShopifyRedirect( URIHandler ):
    # Renders a app page
    def get(self):
        # Request varZ from us
        app          = self.request.get( 'app' )
        
        # Request varZ from Shopify
        shopify_url  = self.request.get( 'shop' )
        shopify_sig  = self.request.get( 'signature' )
        store_token  = self.request.get( 't' )
        shopify_timestamp = self.request.get( 'timestamp' )

        # Get the store or create a new one
        client = ClientShopify.get_or_create(shopify_url, store_token, self, app)
        
        # initialize session
        session = get_current_session()
        session.regenerate_id()
        
        # remember form values
        session['correctEmail'] = client.email
        session['email']        = client.email
        session['reg-errors']   = []
        
        logging.info("CLIENT: %s" % client.email)

        # Cache the client!
        self.db_client = client

        # TODO: apps on shopify have to direct properly
        # the app name has to corespond to AppnameWelcome view
        redirect_url = url('%sWelcome' % app)

        if redirect_url != None:
            redirect_url = '%s?%s' % (redirect_url, self.request.query_string)
        elif app == 'referral':
            redirect_url = '/r/shopify?%s' % self.request.query_string
        elif app == 'sibt':
            redirect_url = '/s/shopify?%s' % self.request.query_string
        elif app == 'buttons':
            redirect_url = '/b/shopify/welcome?%s' % self.request.query_string
        else:
            redirect_url = '/'
        logging.info("redirecting app %s to %s" % (app, redirect_url))
        self.redirect(redirect_url)

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

