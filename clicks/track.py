#!/usr/bin/python
# track.py
__author__      = "Sy Khader"
__copyright__   = "Copyright 2011, The Willet Corporation"

import re, logging, Cookie, os, urllib, simplejson

from google.appengine.api import taskqueue
from google.appengine.api import mail
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

# models
from models.link import get_link_by_willt_code, create_link, save_tweet
from models.campaign import get_campaign_by_id
from models.user import get_or_create_user_by_twitter

# helpers
from util.helpers import set_clicked_cookie, is_blacklisted, set_referral_cookie, set_referrer_cookie
from util.consts import *

class TrackWilltURL( webapp.RequestHandler ):
    """This handler tracks click-throughs on a given code. It tests
       for the presence of a cookie that it also sets in order to ensure
       incremental click-throughs are unique"""

    def get( self, code ):
        link = get_link_by_willt_code(code)
        if not link:
            self.redirect("/")
            return
        #logging.info('Link %s %s clicks: %d' % (link.target_url, link.willt_url_code, link.count_clicks()))
        
        clickCookie = self.request.cookies.get(code, False)
        partialCookie = None
        if not clickCookie and not is_blacklisted(self.request.headers['User-Agent']):
            logging.info("WHO IS THIS? -> " + self.request.headers['User-Agent'])
            link.increment_clicks()
            logging.info('After Link %s %s clicks: %d' % (link.target_url, link.willt_url_code, link.count_clicks()))
            #partialCookie = set_referrer_cookie(link.campaign.uuid, link.willt_url_code, partialCookie)
            partialCookie = set_clicked_cookie(code, partialCookie)

            # Tell Mixplanel that we got a click
            taskqueue.add( queue_name = 'mixpanel', 
                           url        = '/mixpanel', 
                           params     = {'event'          : 'Clicks', 
                                         'campaign_uuid'  : link.campaign.uuid,
                                         'twitter_handle' : link.user.get_attr('twitter_handle')} )

        set_referral_cookie(self.response.headers, code, partialCookie)
        self.redirect(link.target_url)
        return
            

class DynamicLoader(webapp.RequestHandler):
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


class UpdateTwitterGraph(webapp.RequestHandler):
    """Updates the twitter graph with a user's latest information after
       fresh tweet"""
    def post(self):
        screen_name = self.request.get('handle')
        name        = self.request.get('name')
        followers   = self.request.get('follows')
        profile_pic = self.request.get('img')
        tweet       = self.request.get('tweet')
        willt_url_code = self.request.get('willt_c')
        user        = None
        logging.info("Updating Twitter Graph with: screen_name=%s name=%s fllw=%s pic=%s tweet=%s willt_url_code=%s" % (screen_name, name, followers, profile_pic, tweet, willt_url_code) )

        # create our user
        logging.info("SCREEN NAME %s" % screen_name)
        if len(screen_name) > 0:
            logging.info("Fetching a user for %s" % screen_name)

            # check to see if this user has a referral cookie set
            referrer_code = self.request.cookies.get('referral', None)
            referrer = None
            logging.info(referrer_code)
            if referrer_code:
                referral_link = get_link_by_willt_code(referrer_code)
                if referral_link and referral_link.user:
                    referrer = referral_link.user
            
            user = get_or_create_user_by_twitter(screen_name, name, int(followers), profile_pic, referrer)
            #logging.info("USER NOW %r" % user)
            
            #logging.info("Fetching a link for %s" % willt_url_code)
            link = get_link_by_willt_code(willt_url_code)
            #logging.info("LINK: %r" % link)
            
            #logging.info("Does link have a user? %s %r (it shouldn't have a user here)" % (link.user != None, link.user))
            link.user = user
            link.put()

            #logging.info("Does link have a user? %s %r (should have a user here)" % (link.user != None, link.user))

            #logging.info("Link has a campaign? %s %r" % (link.campaign != None, link.campaign))
            #logging.info("Campaign has %d shares before" % link.campaign.get_shares_count())
            link.campaign.increment_shares()
            #logging.info("Campaign has %d shares after (Should be before + 1)" % link.campaign.get_shares_count())
        else:
            #logging.info("NO TWITTER HANDLE PROVIDED. EXCEPTION")
            raise Exception("No twitter handle provided")

        if len(screen_name) == 0 or user.get_attr('twitter_name') == '' or user.get_attr('twitter_pic_url') == '':
            logging.error("invalid data provided " + str(self.request))
            mail.send_mail(sender="wil.lt error reporting <Barbara@wil.lt>",
                       to="wil.lt tech support <support@wil.lt>",
                       subject="Javascript /t callback error",
                       body= user.get_attr('twitter_handle') + str(self.request))

        # save the tweet text that we received from the @anywhere callback
        # to the Link. It will late be looked up for a tweet id
        logging.info("Tweet: %s" % tweet)
        if len(tweet) > 0:
            t = save_tweet(willt_url_code, tweet, user, link)
                
        self.response.out.write("ok")


class TrackCallbackError(webapp.RequestHandler):
    """Notifies us via email of errors when trying to update our twitter
       graph with data from the @anywhere callback"""

    def post(self):
        payload = self.request.get('payload')
        data    = self.request.get('data')
        msg     = self.request.get('msg')

        mail.send_mail(sender="wil.lt error reporting <Barbara@wil.lt>",
                       to="wil.lt tech support <support@wil.lt>",
                       subject="Javascript /t callback error",
                       body= str(payload) + "\n" + str(data) + "\n" + str(msg))
        
        self.response.out.write("Error emailed")

def main():
    application = webapp.WSGIApplication([
        (r'/willet', DynamicLoader), # generate the sharing script
        (r"/tweet", UpdateTwitterGraph),       # update our graph after a fresh tweet
        (r"/trackErr", TrackCallbackError), # track errors in the @anywhere callback
        (r"/(.*)", TrackWilltURL)],       # track the click-through
        debug=USING_DEV_SERVER)
    run_wsgi_app(application)

if __name__ == "__main__":
    main()

