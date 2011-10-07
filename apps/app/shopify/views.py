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
from apps.user.models import get_user_by_cookie, User, get_or_create_user_by_cookie
from apps.client.models import Client, get_or_create_shopify_store
from apps.order.models import *
from apps.stats.models import Stats

from util.gaesessions import get_current_session
from util.helpers     import *
from util.urihandler  import URIHandler
from util.consts      import *

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

        # Try to get the Client if they are logged in
        client = self.get_client() 
        if client is None:

            # Ensure the 'http' is in the URL
            if 'http' not in shopify_url:
                shopify_url = 'http://%s' % shopify_url
            
            #logging.info('asd')
            # Get the store or create a new one
            client = get_or_create_shopify_store(shopify_url, store_token, self, app)
            
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

        # TODO write a smart importer here so we don't have to hardcode these
        # self.redirect(reverse(app+'Welcome'))
        redirect_url = url('%sWelcome' % app)
        if redirect_url != None:
            logging.info("redirecting to %s" % redirect_url)
            self.redirect('%s?%s' % (redirect_url, self.request.query_string))
        elif app == 'referral':
            logging.info("GOING TO EDIT")
            self.redirect('/r/shopify?%s' % self.request.query_string)
        elif app == 'sibt':
            self.redirect('/s/shopify?%s' % self.request.query_string)
        elif app == 'buttons':
            self.redirect('/b/shopify/?%s' % self.request.query_string)
        else:
            logging.info("GOING HOME %s" % app)
            self.redirect( '/' )

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

