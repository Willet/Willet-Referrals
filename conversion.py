#!/usr/bin/python

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc"

import re, urllib

from django.utils import simplejson as json
from google.appengine.api import urlfetch, memcache
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app
from time import time

from models.campaign import Campaign, get_campaign_by_id
from models.user import get_user_by_cookie
from util.helpers import *
from util.urihandler import URIHandler
from util.consts import *

class PostConversion( URIHandler ):
    
    def post(self):
        logging.info('Posting a conversion notification to a Client!')
        referree_uid  = self.request.get( 'referree_uid' )
        campaign_uuid = self.request.get( 'campaign_uuid' )
        campaign      = get_campaign_by_id( campaign_uuid )
        user          = get_user_by_cookie( self ) # probably None, but why not try it!

        if campaign == None:
            # What do we do here?
            return
        
        referrer_uid  = self.request.cookies.get('referrer_%s' % campaign_uuid, False)
        # Only POST if they have a referrer cookie!
        if referrer_uid:

            # Store a 'Conversion' in our DB for tracking purposes
            create_conversion( referrer_uid, campaign, user )

            # Tell the Client by POSTing to their webhook URL
            data = { 'timestamp' : str( time() ),
                     'referrer_id' : referrer_uid,
                     'referree_id' : referree_uid }
            payload = urllib.urlencode( data )

            logging.info("Conversion: Posting to %s (%s referred %s)" % (campaign.webhook_url, referrer_uid, referree_uid) )
            result = urlfetch.fetch( url     = campaign.webhook_url,
                                     payload = payload,
                                     method  = urlfetch.POST,
                                     headers = {'Content-Type': 'application/x-www-form-urlencoded'} )
            
            if result.status_code != 200:
                # What do we do here?
                logging.error("Conversion POST failed: %s (%s referred %s)" % (campaign.webhook_url, referrer_uid, referree_uid) )
                return

            # Tell Mixplanel a client has a conversion
            taskqueue.add( queue_name = 'mixpanel', 
                           url        = '/mixpanel', 
                           params     = {'event'            : 'Conversion', 
                                         'campaign_uuid'    : campaign_uuid,
                                         'supplied_user_id' : referrer_uid} ) 

##---------------------------------------------------------------------------##
##------------------------- The URI Router ----------------------------------##
##---------------------------------------------------------------------------##
def main():
    application = webapp.WSGIApplication([
        (r'/conversion', PostConversion),
        ], debug=USING_DEV_SERVER)
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
