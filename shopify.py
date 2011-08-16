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

def getShopifyOrder( campaign_uuid, order_id ):
    campaign = get_campaign_by_uuid( campaign_uuid )

    url = '%s/admin/orders/#%s.json' % ( campaign.target_url, order_id )
    username = SHOPIFY_API_KEY
    password = SHOPIFY_API_PASSWORD

    # this creates a password manager
    passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
    # because we have put None at the start it will always
    # use this username/password combination for  urls
    # for which `theurl` is a super-url
    passman.add_password(None, theurl, username, password)

    # create the AuthHandler
    authhandler = urllib2.HTTPBasicAuthHandler(passman)

    opener = urllib2.build_opener(authhandler)

    # All calls to urllib2.urlopen will now use our handler
    # Make sure not to include the protocol in with the URL, or
    # HTTPPasswordMgrWithDefaultRealm will be very confused.
    # You must (of course) use it when fetching the page though.
    urllib2.install_opener(opener)

    # authentication is now handled automatically for us
    result = urllib2.urlopen(theurl)

    if result.status_code != 200:
        # Call failed ...
        # handle gracefully
        return # TODO(Barbara): fix this in the future

    order = json.loads( result.content )['order'] # Fetch the order


##-----------------------------------------------------------------------------##
##------------------------- The URI Router ------------------------------------##
##-----------------------------------------------------------------------------##
def main():
    application = webapp.WSGIApplication([ ], debug=USING_DEV_SERVER)
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
