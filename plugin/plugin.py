#!/usr/bin/python

# plugin.py 
# request handlers for the willet social plugin
__author__      = "Sy Khader"
__copyright__   = "Copyright 2011, The Willet Corporation"

import os, logging, urllib, simplejson

from google.appengine.api import taskqueue
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

# models
from models.campaign import get_campaign_by_id
from models.link import create_link, get_link_by_willt_code
from models.oauth import OAuthClient, tweet
from models.testimonial import create_testimonial
from models.user import get_or_create_user_by_email, get_or_create_user_by_facebook, get_user_by_uuid, get_user_by_cookie

# helpers
from util.consts import *
from util.emails import Email
from util.helpers import read_user_cookie, generate_uuid, get_request_variables


class ServeSharingPlugin(webapp.RequestHandler):
    """When requested serves a plugin that will contain various functionality
       for sharing information about a purchase just made by one of our clients"""

    def get(self, input_path):
        template_values = {}
        rq_vars = get_request_variables(['ca_id', 'uid'], self)
        origin_domain = os.environ['HTTP_REFERER'] if\
            os.environ.has_key('HTTP_REFERER') else 'UNKNOWN'

        # Grab a User if we have a cookie!
        user = get_user_by_cookie(self)
        user_email = user.get_attr('email') if user and\
            user.get_attr('email') != '' else "Your Email"
        user_found = True if user is not None else False
        
        campaign = get_campaign_by_id(rq_vars['ca_id'])
        
        # If they give a bogus campaign id, show the landing page campaign!
        logging.info(campaign)
        if campaign == None:
            template_values = {
                'NAME' : NAME,
                
                'text': "",
                'willt_url' : URL,
                'willt_code': "",
                'campaign_uuid' : "",
                'target_url' : URL,
                
                'user' : user,
                'user_email' : user_email,
                'supplied_user_id' : user_id,
            }
        else:
            # Make a new Link
            link = create_link(campaign.target_url, campaign, origin_domain, rq_vars['uid'])
            logging.info("link created is %s" % link.willt_url_code)

            # Create the share text
            if campaign.target_url in campaign.share_text:
                share_text = campaign.share_text.replace( campaign.target_url, link.get_willt_url() )
            else:
                share_text = campaign.share_text + " " + link.get_willt_url()
            
            template_values = {
                'URL' : URL,
                'NAME' : NAME,
                
                'campaign' : campaign,
                'campaign_uuid' : campaign.uuid,
                'text': share_text,
                'willt_url' : link.get_willt_url(),
                'willt_code': link.willt_url_code,
                
                'user': user,
                'supplied_user_id': rq_vars['uid'],
                'user_email': user_email,
                'user_found': str(user_found).lower()
            }
        
        if self.request.url.startswith('http://localhost:8080'):
            template_values['BASE_URL'] = self.request.url[0:21]
        else:
            template_values['BASE_URL'] = URL

        if 'widget' in input_path:
            path = os.path.join(os.path.dirname(__file__), 'html/top.html')
        else:
            path = os.path.join(os.path.dirname(__file__), 'html/bottom.html')
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
        
        rq_vars = get_request_variables(['m', 'wcode'], self)
        user = get_user_by_cookie(self)

        if user and getattr(user, 'twitter_access_token', None) and message and\
            willt_code:
            logging.info("tweeting: " + message)
            twitter_result = tweet(user.twitter_access_token, rq_vars['m'])
            user.update_twitter_info(twitter_handle=twitter_result['user']['screen_name'],
                twitter_profile_pic=twitter_result['user']['profile_image_url_https'],
                twitter_name=twitter_result['user']['name'],
                twitter_followers_count=twitter_result['user']['followers_count'])
            link = get_link_by_willt_code(rq_vars['wcode'])
            if link:
                link.tweet_id = twitter_result['id_str']
                link.user = user
                link.save()
            self.response.headers.add_header("Content-type", 'text/javascript')
            self.response.out.write("<script type='text/javascript'>console.log(window.opener.shareComplete()); window.close();</script>")

        else: 
            client = OAuthClient(service, self)

            if action in client.__public__:
                if action == 'login':
                    logging.info("We didn't recognize you so we're sending you to oauth with your message: " + message)
                    self.response.out.write(getattr(client, action)(rq_vars['m'],
                                                                    rq_vars['wcode']))
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
        via_willet = self.request.get( 'via_willet' )
        
        # check to see if this user has a referral cookie set
        referrer_code = self.request.cookies.get('referral', None)
        referrer = None
        logging.info(referrer_code)
        if referrer_code:
            referral_link = get_link_by_willt_code(referrer_code)
            if referral_link and referral_link.user:
                referrer = referral_link.user
        
        # Get the User
        user = get_or_create_user_by_email(from_addr, referrer, self)
        
        # Get the Link & update it
        link = get_link_by_willt_code(willt_url_code)
        if link:
            link.user = user
            link.put()

            for i in range(0, to_addrs.count(',')):
                link.campaign.increment_shares()

        # Save this Testimonial
        create_testimonial(user=user, message=msg, link=link)

        # Send off the email if they don't want to use Gmail
        if via_willet and to_addrs != '':
            Email.invite( infrom_addr=from_addr, to_addrs=to_addrs, msg=msg, url=url, campaign=link.campaign)


class FacebookCallback( webapp.RequestHandler ):

    def post( self ):
        rq_vars = get_request_variables(['fb_id', 'fb_token', 'share_id',
                                         'first_name', 'last_name', 
                                         'willt_url_code', 'gender', 'verified',
                                         'email', 'msg'], self)

        # check to see if this user has a referral cookie set
        referrer_code = self.request.cookies.get('referral', None)
        referrer = None
        logging.info(referrer_code)
        if referrer_code:
            referral_link = get_link_by_willt_code(referrer_code)
            if referral_link and referral_link.user:
                referrer = referral_link.user
        
        # Grab the User!
        user = get_or_create_user_by_facebook(rq_vars['fb_id'], rq_vars['first_name'], 
                                              rq_vars['last_name'], rq_vars['email'], 
                                              rq_vars['referrer'], rq_vars['verified'], 
                                              rq_vars['gender'], rq_vars['fb_token'], self)
        
        # Grab the Link & update it!
        link = get_link_by_willt_code(rq_vars['willt_url_code'])
        if link:
            link.user = user
            link.facebook_share_id = rq_vars['share_id']
            link.save()

            link.campaign.increment_shares()

            # Save this Testimonial
            create_testimonial(user=user, message=rq_vars['msg'], link=link)


class FacebookShare(webapp.RequestHandler):
    """This handler attempts to share a status message for a given user
       based on a pre-stored oauth key.
       Responses:
            ok - facebook share successful
            fail - facebook denied post request
            deadlink - link not found
            notfound - user or fb info not found"""

    def post(self):
        rq_vars = get_request_variables(['msg', 'wcode'], self)
        user = get_user_by_cookie(self)
        logging.info(user)
        if user and hasattr(user, 'facebook_access_token')\
            and hasattr(user, 'fb_identity'):

            link = get_link_by_willt_code(rq_vars['wcode'])

            if link:
                facebook_share_url = "https://graph.facebook.com/%s/feed"%user.fb_identity
                params = urllib.urlencode({'access_token': user.facebook_access_token,
                                           'message': rq_vars['msg'] })
                fb_response = urllib.urlopen(facebook_share_url, params)
                fb_results = simplejson.loads(fb_response.read())
                if fb_results.has_key('id'):
                    link.facebook_share_id = fb_results['id']
                    link.user = user;
                    link.save()
                    self.response.out.write('ok')
                    taskqueue.add(url = '/fetchFB',
                                  params = {'fb_id': user.fb_identity})
                                            
                else:
                    self.response.out.write('fail')
                    logging.info(fb_results)

            else: 
                self.response.out.write('deadlink')

        else:
            self.response.out.write('notfound')
        

def main():
    application = webapp.WSGIApplication([
        (r'/fbCallback', FacebookCallback),
        (r'/fbShare', FacebookShare),
        (r'/sendEmailInvites', SendEmailInvites),
        (r'/share', DynamicSocialLoader),
        (r'/oauth/(.*)/(.*)', TwitterOAuthHandler),
        (r'/(.*)', ServeSharingPlugin)],
        debug=USING_DEV_SERVER)
    run_wsgi_app(application)

if __name__ == "__main__":
    main()

