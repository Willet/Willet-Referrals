#!/usr/bin/python

__author__      = "Barbara Macdonald"
__copyright__   = "Copyright 2011, Barbara"

import base64, logging, urllib, urllib2

from django.utils import simplejson as json
from google.appengine.api import urlfetch
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

from util.consts import *

##-----------------------------------------------------------------------------##
##------------------------- The Dos -------------------------------------------##
##-----------------------------------------------------------------------------##

class SendToMixpanel( webapp.RequestHandler ):
    
    def post( self ):
        event          = self.request.get( 'event' )
        campaign_uuid  = self.request.get( 'campaign_uuid' )
        twitter_handle = self.request.get( 'twitter_handle' )
        user_id        = self.request.get( 'supplied_user_id' )
        num            = self.request.get( 'num' )

        user = twitter_handle if twitter_handle != '' else user_id

        # ----------------------------------------------------------------------
        # Store the Per-User Data
        data = { 'token'    : MIXPANEL_TOKEN,
                 'user'     : user,
                 'campaign' : campaign_uuid,
                 'bucket'   : campaign_uuid }

        params = {"event": "%s_%s_%s" % (event, campaign_uuid, user), "properties": data}
        payload = base64.b64encode(json.dumps(params))

        # Save the campaign data in a bucket
        result = urlfetch.fetch( url     = '%sdata=%s' % (MIXPANEL_API_URL, payload),
                                 method  = urlfetch.GET,
                                 headers = {'Content-Type': 'application/x-www-form-urlencoded'} )
        
        # ----------------------------------------------------------------------
        # Store the Per-Campaign data
        data = { 'token'    : MIXPANEL_TOKEN,
                 'user'     : user,
                 'campaign' : campaign_uuid,
                 'bucket'   : campaign_uuid }

        params = {"event": "%s_%s" % (event,campaign_uuid), "properties": data}
        payload = base64.b64encode(json.dumps(params))

        # Save the campaign data in a bucket
        result = urlfetch.fetch( url     = '%sdata=%s' % (MIXPANEL_API_URL, payload),
                                 method  = urlfetch.GET,
                                 headers = {'Content-Type': 'application/x-www-form-urlencoded'} )

        # ----------------------------------------------------------------------
        # Now, save the data for us to see
        data = { 'token'    : MIXPANEL_TOKEN,
                 'user'     : user,
                 'campaign' : campaign_uuid }

        params = {"event": "%s" % (event), "properties": data}
        payload = base64.b64encode(json.dumps(params))

        result = urlfetch.fetch( url     = '%sdata=%s' % (MIXPANEL_API_URL, payload),
                                 method  = urlfetch.GET,
                                 headers = {'Content-Type': 'application/x-www-form-urlencoded'} )


        

##-----------------------------------------------------------------------------##
##------------------------- The URI Router ------------------------------------##
##-----------------------------------------------------------------------------##
def main():
    application = webapp.WSGIApplication([ (r'/mixpanel', SendToMixpanel), ], debug=USING_DEV_SERVER)
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
