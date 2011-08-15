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

def getShopifyOrder( order_id ):
    client shop url

/admin/orders/#{id}.json




##-----------------------------------------------------------------------------##
##------------------------- The URI Router ------------------------------------##
##-----------------------------------------------------------------------------##
def main():
    application = webapp.WSGIApplication([ ], debug=USING_DEV_SERVER)
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
