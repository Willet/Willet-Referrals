#!/usr/bin/python

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc"

import re, urllib

from django.utils import simplejson as json
from google.appengine.api import urlfetch, memcache
from google.appengine.ext import webapp
from google.appengine.api import taskqueue
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

from models.campaign import Campaign, ShareCounter, get_campaign_by_id
from models.client import Client
from models.link import *
from models.user import User, get_user_by_twitter, get_or_create_user_by_twitter

from util.consts import *
from util.helpers import *
from util.urihandler import URIHandler

##-----------------------------------------------------------------------------##
##------------------------- The Dos -------------------------------------------##
##-----------------------------------------------------------------------------##

class Admin( URIHandler ):
    
    @admin_required
    def get(self, admin):
        """
        links = Link.all()

        for l in links:
            if l.target_url != 'http://www.wil.lt' and l.target_url != "http://www.vidyard.com":
                c = l.count_clicks()

                if c > 0:
                    if l.user:
                        # Tell Mixplanel that we got a click
                        taskqueue.add( queue_name = 'mixpanel', 
                                       url        = '/mixpanel', 
                                       params     = {'event' : 'Clicks', 'num' : c, 'campaign_uuid' : l.campaign.uuid, 'twitter_handle' : l.user.get_attr('twitter_handle')} )

        return
        str = ""
        for c in Client.all():
            e  = c.email
            pw = c.passphrase != None

            others = Client.all().filter( 'email =', e )
            for o in others:
                if o.key() == c.key():
                    continue
                
                if o.campaigns.count() == 0:
                    str += "<p> Deleting %s (%s). %s (%d) is in here.</p>" % (o.email, o.passphrase, e, c.campaigns.count())
                    o.delete()
            for o in clients:
                if o.key() == c.key():
                    continue

                if o.email == e:
                    #for camps in o.campaigns:
                        #str += "<p> Reassigning %s to %s</p>" % (camps.title, c.email)
                        #camps.client = c
                        #camps.put()
                    
                    if o.campaigns.count() == 0:
                        str += "<p> Deleting %s (%s). %s is in here.</p>" % (o.email, o.passphrase, e)
                        #o.delete()
        self.response.out.write( str )
        campaigns = Campaign.all()

        str = ""
        for c in campaigns:
            clicks = c.count_clicks()

            if clicks != 0 and c.client.email != 'z4beth@gmail.com' and c.client.email != 'sy@sayedkhader.com':
                str += "<p> Campaign: '%s' URL: %s Owner: %s Tweets: %d Clicks: %d </p>" % (c.title, c.target_url, c.client.email, c.get_shares_count(), clicks)
        
        self.response.out.write( str )
        """
        links = Link.all()
        str = " Bad Links "
        for l in links:
            clicks = l.count_clicks()
            if l.user == None and clicks != 0:
                str += "<p> URL: %s Clicks: %d Code: %s Campaign: %s Time: %s</p>" % (l.target_url, clicks, l.willt_url_code, l.campaign.title, l.creation_time)

        self.response.out.write( str )


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

##-----------------------------------------------------------------------------##
##------------------------- The URI Router ------------------------------------##
##-----------------------------------------------------------------------------##
def main():
    application = webapp.WSGIApplication([
        (r'/admin', Admin),
        (r'/cleanBadLinks', CleanBadLinks),
        ], debug=USING_DEV_SERVER)
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
