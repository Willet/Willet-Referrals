#!/usr/bin/env python

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc"

import re, hashlib, urllib

from django.utils import simplejson as json
from google.appengine.api import urlfetch, memcache
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api.datastore_errors import BadValueError
from time import time

from apps.app.models import *
from apps.order.models import *
from apps.link.models import Link, get_link_by_willt_code
from apps.user.models import User, get_or_create_user_by_email, get_user_by_cookie

from util.helpers import *
from util.urihandler import URIHandler
from util.consts import *
from util.gaesessions import get_current_session

class PostConversion( URIHandler ):
    def post(self):
        referree_uid = self.request.get( 'referree_uid' )
        app_uuid     = self.request.get( 'app_uuid' )
        app          = get_app_by_id( app_uuid )
        order_num    = self.request.get( 'order_num' )
        user         = get_user_by_cookie( self ) # probably None, but why not try it!

        if app == None:
            # What do we do here?
            return
        
        referrer_willt_url = self.request.cookies.get('referrer_%s' % app_uuid, False)

        # Only POST if they have a referrer cookie!
        if referrer_willt_url:
            link = get_link_by_willt_code( referrer_willt_url )
            logging.info('Posting a conversion notification to a Client!')

            # Store a 'Conversion' in our DB for tracking purposes
            create_conversion( link, app, referree_uid, user, order_num )

            # Tell the Client by POSTing to their webhook URL
            data = { 'timestamp'   : str( time() ),
                     'referrer_id' : link.supplied_user_id,
                     'referree_id' : referree_uid }
            payload = urllib.urlencode( data )

            logging.info("Conversion: Posting to %s (%s referred %s)" % (app.webhook_url, link.supplied_user_id, referree_uid) )
            result = urlfetch.fetch( url     = app.webhook_url,
                                     payload = payload,
                                     method  = urlfetch.POST,
                                     headers = {'Content-Type': 'application/x-www-form-urlencoded'} )
            
            if result.status_code != 200:
                # What do we do here?
                logging.error("Conversion POST failed: %s (%s referred %s)" % (app.webhook_url, link.supplied_user_id, referree_uid) )
                return

class EmailerCron( URIHandler ):
    def get( self ):
        apps = App.all()

        for c in apps:
            #logging.info("Working on %s" % c.title)

            if not c.emailed_at_10 and c.client:
                #logging.info('count %s' % c.get_shares_count() )
                if c.get_shares_count() >= 10:

                    taskqueue.add( queue_name='emailer', 
                                   url='/emailerQueue', 
                                   name= 'EmailingApp%s' % c.uuid,
                                   params={'app_id' : c.uuid,
                                           'email' : c.client.email} )

class EmailerQueue( URIHandler ):
    def post( self ):
        email_addr  = self.request.get('email')
        app_id = self.request.get('app_id')

        # Send out the email.
        Email.first10Shares( email_addr )

        # Set the emailed flag.
        app = get_app_by_id( app_id )
        app.emailed_at_10 = True
        app.put()
