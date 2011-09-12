#!/usr/bin/env python

__author__      = "Sy Khader"
__copyright__   = "Copyright 2011, The Willet Corporation"

import re, logging, Cookie, os, urllib, urllib2, time, datetime, simplejson

from google.appengine.api import mail, taskqueue
from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

# models
from apps.link.models import * 
from apps.campaign.models import get_campaign_by_id, Campaign
from apps.user.models import get_or_create_user_by_twitter

# helpers
from util.helpers import set_clicked_cookie, is_blacklisted, set_referral_cookie, set_referrer_cookie
from util.consts import *


class TrackWilltURL( webapp.RequestHandler ):
    """This handler tracks click-throughs on a given code. It tests
       for the presence of a cookie that it also sets in order to ensure
       incremental click-throughs are unique"""

    def get( self, code ):
        logging.info("PATH %s" % self.request.url )
        if 'social-referral.appspot.com' not in self.request.url:
            self.redirect( 'http://social-referral.appspot.com/%s' % code )
            return

        link = get_link_by_willt_code(code)
        if not link:
            self.redirect("/")
            return
        #logging.info('Link %s %s clicks: %d' % (link.target_url, link.willt_url_code, link.count_clicks()))
        
        clickCookie = self.request.cookies.get(code, False)
        if not clickCookie and not is_blacklisted(self.request.headers['User-Agent']):
            logging.info("WHO IS THIS? -> " + self.request.headers['User-Agent'])
            link.increment_clicks()
            logging.info('After Link %s %s clicks: %d' % (link.target_url, link.willt_url_code, link.count_clicks()))
            set_referrer_cookie(self.response.headers, link.campaign.uuid, link.willt_url_code)
            set_clicked_cookie(self.response.headers, code)

            # Tell Mixplanel that we got a click
            taskqueue.add( queue_name = 'mixpanel', 
                           url        = '/mixpanel', 
                           params     = {'event'          : 'Clicks', 
                                         'campaign_uuid'  : link.campaign.uuid,
                                         'twitter_handle' : link.user.get_attr('twitter_handle') if link.user else ''} )

        set_referral_cookie(self.response.headers, code)
        self.redirect(link.target_url)
        return
            

class DynamicLinkLoader(webapp.RequestHandler):
    """Generates a customized javascript source file pre-loaded
       with a unique URL to share. A 'link' model is created in the
       datastore and will be deleted by cron if the associated tweet
       is not found in the tweeting user's stream"""

    def get(self):
        template_values = {}
        campaign_id = self.request.get('ca_id')
        user_id = self.request.get('uid')
        origin_domain = os.environ['HTTP_REFERER'] if\
            os.environ.has_key('HTTP_REFERER') else 'UNKNOWN'

        logging.info(origin_domain)
        campaign = get_campaign_by_id(campaign_id)
        
        # If they give a bogus campaign id, show the landing page campaign!
        if campaign == None:
            template_values = {
                'text': "",
                'willt_url' : URL,
                'willt_code': "",
                'campaign_uuid' : "",
                'target_url' : URL
            }
        else:
            link = create_link(campaign.target_url, campaign, origin_domain, user_id)
            logging.info("link created is %s" % link.willt_url_code)

            if campaign.target_url in campaign.share_text:
                share_text = campaign.share_text.replace( campaign.target_url, link.get_willt_url() )
            else:
                share_text = campaign.share_text + " " + link.get_willt_url()

            template_values = {
                'text': share_text.replace("\"", "'"),
                'willt_url' : link.get_willt_url(),
                'willt_code': link.willt_url_code,
                'campaign_uuid' : campaign.uuid,
                'target_url' : campaign.target_url,
                'redirect_url' : campaign.redirect_url if campaign.redirect_url else "",
                'MIXPANEL_TOKEN' : MIXPANEL_TOKEN
            }
        
        path = os.path.join(os.path.dirname(__file__), 'templates/willet.html')
        self.response.out.write(template.render(path, template_values))
        return

class getUncheckedTweets( URIHandler ):
    """Gets the unchecked tweets to see whether or not they were tweeted and
       if so then grab the tweet id's."""

    @admin_required
    def get(self, admin):
        twitter_date_fmt = '%a %b %d %H:%M:%S %Y'
        unread_tweets = get_some_tweets()
        counters = {
            'deleted': 0,
            'user-deleted': 0,
            'not-found': 0,
            'found': 0,
            'dangling': 0
        }
        datetime_interval = datetime.datetime.now()-datetime.timedelta(hours=1)
        check_interval = datetime.datetime.combine(datetime_interval,
                                                   datetime_interval.time())
        for ut in unread_tweets:
            # query twitter for tweet
            params = urllib.urlencode({
                'include_entities': False,
                'include_rts': False,
                'screen_name': ut.user.get_attr('twitter_handle')
            })
            logging.info(TWITTER_TIMELINE_URL + params)
            twitter_response = urllib.urlopen(TWITTER_TIMELINE_URL + params)
            twitter_results = simplejson.loads(twitter_response.read())

            logging.info('TWITTER: %r' % twitter_results)

            if type(twitter_results) is dict and\
                twitter_results.has_key('error') and twitter_results['error'] > 0:
                self.response.out.write(twitter_results['error'])
                return

            earliest = { 'created_at': None, 'id': None }
            # find the earliest matching tweet
            for t in twitter_results:
                # have to snip timezome since time.strptime doesn't support it
                date_without_tz = t['created_at'].replace("+0000 ", "")
                # parse the twitter provided date string into a datetime object
                tweet_date = datetime.datetime(*time.strptime(date_without_tz,
                                                              twitter_date_fmt)[:6])
                if ut.get_willt_url() in t['text'] and\
                   (earliest['created_at'] is None or\
                    tweet_date < earliest['created_at']):
                    earliest = { 'created_at': tweet_date, 
                                 'id': t['id'],
                                 'user': t['user']['screen_name']}

            # if we found a tweet, grab the url from it, lookup the associated Link
            # and save the tweet info to it
            if earliest['created_at'] is not None:

                link = get_link_by_willt_code(ut.willt_url_code)

                if link:

                    if link.user.get_attr('twitter_handle') != earliest['user']:#should never happen
                        tweet.delete()
                        counters['user-deleted'] += 1
                        counters['deleted'] += 1
                        raise Exception("We got the wrong user information from\
                        the @anywhere callback")
                    else:
                        link.tweet_id = str(earliest['id'])
                        link.put()
                        ut.delete()
                        counters['found'] += 1

                else:
                    ut.delete()
                    raise Exception("Link not found for code: " + ut.willt_url_code)
            else:
                # our search for the tweet in the user's stream returned nothing
                counters['not-found'] += 1
                ut.delete()
        self.response.out.write(counters)


