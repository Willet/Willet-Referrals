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

from apps.campaign.models import Campaign, get_campaign_by_id
from apps.link.models import Link, get_link_by_willt_code
from apps.user.models import get_user_by_cookie

from util.helpers import *
from util.urihandler import URIHandler
from util.consts import *

class PostConversion( URIHandler ):
    
    def post(self):
        referree_uid  = self.request.get( 'referree_uid' )
        campaign_uuid = self.request.get( 'campaign_uuid' )
        order_num = self.request.get('order_num')
        campaign      = get_campaign_by_id( campaign_uuid )
        user          = get_user_by_cookie( self ) # probably None, but why not try it!

        if campaign == None:
            # What do we do here?
            return
        
        referrer_willt_url = self.request.cookies.get('referrer_%s' % campaign_uuid, False)

        # Only POST if they have a referrer cookie!
        if referrer_willt_url:
            link = get_link_by_willt_code( referrer_willt_url )
            logging.info('Posting a conversion notification to a Client!')

            # Store a 'Conversion' in our DB for tracking purposes
            create_conversion( link, campaign, referree_uid, user, order_num )

            # Tell the Client by POSTing to their webhook URL
            data = { 'timestamp'   : str( time() ),
                     'referrer_id' : link.supplied_user_id,
                     'referree_id' : referree_uid }
            payload = urllib.urlencode( data )

            logging.info("Conversion: Posting to %s (%s referred %s)" % (campaign.webhook_url, link.supplied_user_id, referree_uid) )
            result = urlfetch.fetch( url     = campaign.webhook_url,
                                     payload = payload,
                                     method  = urlfetch.POST,
                                     headers = {'Content-Type': 'application/x-www-form-urlencoded'} )
            
            if result.status_code != 200:
                # What do we do here?
                logging.error("Conversion POST failed: %s (%s referred %s)" % (campaign.webhook_url, link.supplied_user_id, referree_uid) )
                return

            # Tell Mixplanel a client has a conversion
            taskqueue.add( queue_name = 'mixpanel', 
                           url        = '/mixpanel', 
                           params     = {'event'            : 'Conversion', 
                                         'campaign_uuid'    : campaign_uuid,
                                         'supplied_user_id' : link.supplied_user_id} ) 


