#!/usr/bin/env python

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc"

import re, urllib

from django.utils import simplejson as json
from google.appengine.api import urlfetch, memcache
from google.appengine.ext import webapp
from google.appengine.api import taskqueue
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

from apps.link.models import Link

from util.consts import *
from util.helpers import *
from util.urihandler import URIHandler

class CleanBadLinks( webapp.RequestHandler ):
    def get(self):
        links = Link.all()

        count = 0
        str   = 'Cleaning the bad links'
        for l in links:
            clicks = l.count_clicks()

            if l.user == None and clicks != 0:
                count += 1
                str   += "<p> URL: %s Clicks: %d Code: %s Campaign: %s Time: %s</p>" % (l.target_url, clicks, l.willt_url_code, l.campaign.title, l.creation_time)

                l.delete()


        logging.info("CleanBadLinks Report: Deleted %d Links. (%s)" % ( count, str ) )


