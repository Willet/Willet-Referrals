#!/usr/bin/env python

__author__      = "Sy Khader"
__copyright__   = "Copyright 2011, The Willet Corporation"

import re, logging, Cookie, os, urllib, urllib2, time, datetime, simplejson

from google.appengine.api import mail, taskqueue
from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

# models
from apps.link.models import Link, get_link_by_willt_code, CodeCounter
from apps.app.models import get_app_by_id, App

# helpers
from util.helpers import admin_required, set_clicked_cookie, is_blacklisted, set_referral_cookie, set_referrer_cookie
from util.consts import *
from util.urihandler import URIHandler

class TrackWilltURL( webapp.RequestHandler ):
    """This handler tracks click-throughs on a given code. It tests
       for the presence of a cookie that it also sets in order to ensure
       incremental click-throughs are unique"""

    def get( self, code ):
        self.response.headers.add_header('P3P', P3P_HEADER)
        logging.info("PATH %s" % self.request.url )
        if APP_DOMAIN not in self.request.url:
            self.redirect( '%s/%s' % (URL, code) )
            return

        # Fetch the Link
        link = Link.get_by_code(code)
        if not link:
            logging.warn ("no link contains the code '%s'" % code)
            self.redirect("/")
            return

        #  Let the App handle the 'click'
        if not is_blacklisted(self.request.headers['User-Agent']):
            logging.info("WHO IS THIS? -> " + self.request.headers['User-Agent'])

            link.app_.handleLinkClick( self, link )
            
            # TODO(Barbara): Remove this when we make Referral app use Actions
            set_clicked_cookie(self.response.headers, code)

        return
            
class InitCodes(webapp.RequestHandler):
    """Run this script to initialize the counters for the willt
       url code generators"""
    def get(self):
        n = 0
        for i in range(20):
            ac = CodeCounter(
                count=i,
                total_counter_nums=20,
                key_name = str(i)
            )
            ac.put()
            n += 1
        self.response.out.write(str(n) + " counters initialized")

class CleanBadLinks( webapp.RequestHandler ):
    def get(self):
        links = Link.all().filter('user =', None)

        count = 0
        str   = 'Cleaning the bad links'
        for l in links:
            clicks = l.count_clicks()
            try:
                if l.user == None and clicks != 0:
                    count += 1
                    str   += "<p> URL: %s Clicks: %d Code: %s Campaign: %s Time: %s</p>" % (l.target_url, clicks, l.willt_url_code, l.campaign.title, l.creation_time)

                    l.delete()
            except Exception,e:
                l.delete()
                logging.warn('probably unable to resolve property: %s' % e)

        logging.info("CleanBadLinks Report: Deleted %d Links. (%s)" % ( count, str ) )

class IncrementCodeCounter(webapp.RequestHandler):
    """ This was getting called every time a willet code was being
        created, usually taking ~100ms. Moved to a task to speed up
        page load times"""
    def post(self):
        def txn(cc):
            cc.count += cc.total_counter_nums
            cc.put()
            return cc
        
        count = self.request.get('count')
        cc = CodeCounter.all().filter('count =', int(count)).get()
        if cc != None:
            returned_cc = db.run_in_transaction(txn, cc) 
            logging.info('incremented code counter %s' % returned_cc)

