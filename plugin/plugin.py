#!/usr/bin/python

# plugin.py 
# request handlers for the willet social plugin
__author__      = "Sy Khader"
__copyright__   = "Copyright 2011, The Willet Corporation"

import os, logging

from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

# models
from models.campaign import get_campaign_by_id
from models.link import create_link, get_link_by_willt_code
from models.oauth import OAuthClient, tweet
from models.user import get_or_create_user_by_email, get_or_create_user_by_facebook, get_user_by_uuid

# helpers
from util.consts import *
from util.emails import Email
from util.helpers import read_user_cookie

class ServeSharingPlugin(webapp.RequestHandler):
    """When requested serves a plugin that will contain various functionality
       for sharing information about a purchase just made by one of our clients"""

    def get(self):
        template_values = {}
        campaign_id = self.request.get('ca_id')
        user_id = self.request.get('uid')
        origin_domain = os.environ['HTTP_REFERER'] if\
            os.environ.has_key('HTTP_REFERER') else 'UNKNOWN'

        campaign = get_campaign_by_id(campaign_id)
        # If they give a bogus campaign id, show the landing page campaign!
        logging.info(campaign)
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
                'campaign_uuid' : campaign.uuid,
                'text': share_text,
                'willt_code': link.willt_url_code,
                'URL' : URL,
                'supplied_user_id' : user_id,
            }
        
        if self.request.url.startswith('http://localhost:8080'):
            template_values['BASE_URL'] = self.request.url[0:21]
        else:
            template_values['BASE_URL'] = URL

        path = os.path.join(os.path.dirname(__file__), 'html/willt.html')
        self.response.out.write(template.render(path, template_values))
        return


class DynamicSocialLoader(webapp.RequestHandler):
    """Dynamically loads the source of an iframe containing a campaign's
       share text. Currently supports: tweet, facebook share, email"""

    def get(self):
        template_values = {}
        campaign_id = self.request.get('ca_id')
        user_id = self.request.get('uid')
        social_type = self.request.get('type')
        origin_domain = os.environ['HTTP_REFERER'] if\
            os.environ.has_key('HTTP_REFERER') else 'UNKNOWN'

        if self.request.url.startswith('http://localhost:8080'):
            template_values['BASE_URL'] = self.request.url[0:21]

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
        template_file = 'twitter.html'
        if social_type == 'fb':
            template_file = 'facebook.html'
        elif social_type == 'e':
            template_file = 'email.html'

        path = os.path.join(os.path.dirname(__file__), 'html/%s' % template_file)
        self.response.out.write(template.render(path, template_values))
        return

class TwitterOAuthHandler(webapp.RequestHandler):

    def get(self, service, action=''):
        
        wuid = read_user_cookie(self)
        message = self.request.get('m')

        user = get_user_by_uuid(wuid);
        if user and user.twitter_access_token:
            twitter_response = tweet(user.twitter_access_token, message)
            logging.info(res);
            
        else: 
            client = OAuthClient(service, self)

            if action in client.__public__:
                if action == 'login':
                    self.response.out.write(getattr(client, action)(message))
                else:
                    self.response.out.write(getattr(client, action)())
            else:
                self.response.out.write(client.login())

class SendEmailInvites( webapp.RequestHandler ):

    def post( self ):
        from_addr = self.request.get( 'from_addr' )
        to_addrs  = self.request.get( 'to_addrs' )
        msg       = self.request.get( 'msg' )
        url       = self.request.get( 'url' )
        willt_url_code = self.request.get( 'willt_url_code' )
        via_gmail = self.request.get( 'via_gmail' )
        
        # check to see if this user has a referral cookie set
        referrer_code = self.request.cookies.get('referral', None)
        referrer = None
        logging.info(referrer_code)
        if referrer_code:
            referral_link = get_link_by_willt_code(referrer_code)
            if referral_link and referral_link.user:
                referrer = referral_link.user
        
        user = get_or_create_user_by_email(from_addr, referrer, self)
        
        link = get_link_by_willt_code(willt_url_code)
        if link:
            link.user = user
            link.put()

            for i in range(0, to_addrs.count(',')):
                link.campaign.increment_shares()

        if not via_gmail and to_addrs != '':
            Email.invite( infrom_addr=from_addr, to_addrs=to_addrs, msg=msg, url=url)

class FacebookCallback( webapp.RequestHandler ):

    def post( self ):
        fb_id           = self.request.get( 'fb_id' )
        first_name      = self.request.get( 'first_name' )
        last_name       = self.request.get( 'last_name' )
        email           = self.request.get( 'email' )
        willt_url_code  = self.request.get( 'willt_url_code' )

        # check to see if this user has a referral cookie set
        referrer_code = self.request.cookies.get('referral', None)
        referrer = None
        logging.info(referrer_code)
        if referrer_code:
            referral_link = get_link_by_willt_code(referrer_code)
            if referral_link and referral_link.user:
                referrer = referral_link.user
        
        user = get_or_create_user_by_facebook(fb_id, first_name, last_name, email, referrer, self)
        
        link = get_link_by_willt_code(willt_url_code)
        if link:
            link.user = user
            link.put()

            link.campaign.increment_shares()

def main():
    application = webapp.WSGIApplication([
        (r'/fbCallback', FacebookCallback),
        (r'/sendEmailInvites', SendEmailInvites),
        (r'/share', DynamicSocialLoader),
        (r'/oauth/(.*)/(.*)', TwitterOAuthHandler),
        (r'/willt', ServeSharingPlugin)],
        debug=USING_DEV_SERVER)
    run_wsgi_app(application)

if __name__ == "__main__":
    main()

