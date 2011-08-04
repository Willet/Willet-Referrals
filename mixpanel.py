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
        num            = self.request.get( 'num' )

        data = { 'token'    : MIXPANEL_TOKEN,
                 'user'     : twitter_handle,
                 'campaign' : campaign_uuid,
                 'bucket'   : campaign_uuid }

        logging.info("%s %s" % ( twitter_handle, campaign_uuid ))

        params = {"event": "%s_%s_%s" % (event,campaign_uuid,twitter_handle), "properties": data}
        payload = base64.b64encode(json.dumps(params))

        if num == None or num == '':
            num = 1

        for i in range( 0, int(num) ):
            #logging.info("MIXPANELLING: %r %s" % ( payload, payload ) )
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
