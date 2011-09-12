#!/usr/bin/env python

"""
Processes for Stats
"""
__all__ = [
    'Client'
]
import hashlib, logging, urllib, urllib2, uuid

from datetime import datetime
from django.utils import simplejson as json

from google.appengine.api import memcache, taskqueue, urlfetch

from apps.stats.models import *
from apps.campaign.models import Campaign, ShareCounter, get_campaign_by_id
from apps.link.models import Link, LinkCounter

from util.consts import *
from util.emails import Email
from util.helpers import *
from util.urihandler import URIHandler

class UpdateCounts( webapp.RequestHandler ):
    def get( self ): 
        stats = Stats.get_stats()
        stats.total_clients    = Client.all().count()
        stats.total_campaigns  = Campaign.all().count()
        stats.total_links      = Link.all().count()
        stats.total_users      = User.all().count()
        stats.put()

class UpdateTweets( webapp.RequestHandler ):
    def get( self ):
        shares = ShareCounter.all()
        total  = 0
        for s in shares:
            total += s.count

        stats = Stats.get_stats()
        stats.total_tweets = total
        stats.put()

class UpdateClicks( webapp.RequestHandler ):
    def get( self ):
        links = LinkCounter.all()
        total  = 0
        for l in links:
            total += l.count

        stats = Stats.get_stats()
        stats.total_clicks = total
        stats.put()

class UpdateLanding( webapp.RequestHandler ):
    def get( self ):
        campaign     = get_campaign_by_id( LANDING_CAMPAIGN_UUID )
        
        if campaign == None:
            return

        total_clicks = campaign.count_clicks()
        results, foo = campaign.get_results( total_clicks )

        # Build the string.
        s = '<div class="span-11 last center" id="landing_influencer_title"> <div class="span-1">&nbsp;</div> <div class="span-1">&nbsp;</div> <div class="span-3">&nbsp;</div> <div class="span-2">&nbsp;</div> <div class="span-2">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Clickthroughs</div> <div class="span-2 last">&nbsp;&nbsp;&nbsp;Klout Score</div> </div>'
        count = 0
        for r in results:
            if r['user']:
                twitter_handle = r['user'].twitter_handle
                s += '<div class="span-11 last influencer landing">'
                
                s += '<div class="span-1 number" title="%s\'s place for this campaign."> %s </div>' % (twitter_handle, r['num'])
                s += '<div class="span-1" title="Click to visit %s on Twitter.com!">' % twitter_handle
                s += '<a href="https://twitter.com/#!/%s">' % twitter_handle
                s += '<img class="profile_pic" src="%s"> </img></a></div>' % r['user'].twitter_pic_url 
                
                s += '<div class="span-3 lower-10" title="%s\'s Real Name"> %s </div>' % (twitter_handle, r['user'].twitter_name)
                s += '<div class="span-3 lower-10" title="Click to visit %s on Twitter!">' % twitter_handle
                s += '<a class="twitter_link" href="https://twitter.com/#!/%s">@%s</a></div>' % (twitter_handle, twitter_handle)
                s += '<div class="span-1 lower-10" title="A count of all clicks this user received for this campaign."> %d </div>' % r['clicks']
            
                s += '<div class="span-2 lower-5 last" title="Click to visit %s on Klout.com!">' % twitter_handle
                s += '<a class="klout_link" href="http://klout.com/#/%s">' % twitter_handle
                s += '<img class="klout_logo" src="/static/imgs/klout_logo.jpg"> </img>'
                s += '<object class="klout_score">%s</object> </a> </div>' % r['kscore']

                s += '</div>'

                count += 1

            if count == 6:
                break;

        stats = Stats.get_stats()
        stats.landing = s
        stats.put()

        self.response.out.write( s )

 
