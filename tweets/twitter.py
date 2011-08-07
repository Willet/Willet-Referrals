#!/usr/bin/python

# API calls to twitter

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc"

import re, logging, urllib2, urllib, simplejson, time, datetime

from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

# models
from models.link import get_unchecked_links, get_some_tweets, get_link_by_willt_code
from models.user import get_or_create_user_by_twitter
from models.campaign import Campaign

from util.consts import *
from util.helpers import *
from util.urihandler import URIHandler

TWITTER_SEARCH_URL = 'https://api.twitter.com/1/statuses/user_timeline.json?'

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
            logging.info(TWITTER_SEARCH_URL + params)
            twitter_response = urllib.urlopen(TWITTER_SEARCH_URL + params)
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

def main():
    application = webapp.WSGIApplication([
        (r'/getTweets', getUncheckedTweets)],
                                         debug=USING_DEV_SERVER)
    run_wsgi_app(application)

if __name__ == "__main__":
    main()

