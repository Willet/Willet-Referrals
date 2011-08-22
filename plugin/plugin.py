#!/usr/bin/python

# plugin.py 
# request handlers for the willet social plugin
__author__      = "Sy Khader"
__copyright__   = "Copyright 2011, The Willet Corporation"


import os, logging, urllib, simplejson

from google.appengine.api import taskqueue, urlfetch
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

# models
from models.campaign import get_campaign_by_id, get_campaign_by_shopify_store
from models.link import create_link, get_link_by_willt_code
from models.oauth import OAuthClient
from models.testimonial import create_testimonial
from models.user import get_or_create_user_by_email, get_or_create_user_by_facebook, get_user_by_uuid, get_or_create_user_by_cookie

# helpers
from util.consts import *
from util.emails import Email
from util.helpers import read_user_cookie, generate_uuid, get_request_variables

class ServeSharingPlugin(webapp.RequestHandler):
    """When requested serves a plugin that will contain various functionality
       for sharing information about a purchase just made by one of our clients"""
    
    def get(self, input_path):
        logging.info('STORE: %s' % self.request.get('store'))
        template_values = {}
        rq_vars = get_request_variables(['ca_id', 'uid', 'store', 'order'], self)
        origin_domain = os.environ['HTTP_REFERER'] if\
            os.environ.has_key('HTTP_REFERER') else 'UNKNOWN'
        
        # Grab a User if we have a cookie!
        user = get_or_create_user_by_cookie(self)
        user_email = user.get_attr('email') if user and\
            user.get_attr('email') != '' else "Your Email"
        user_found = True if hasattr(user, 'fb_access_token') else False
        
        if rq_vars['store'] != '':
            campaign = get_campaign_by_shopify_store( rq_vars['store'] )
            
            taskqueue.add( queue_name='shopifyAPI', 
                           url='/getShopifyOrder', 
                           name= 'shopifyOrder%s%s' % (generate_uuid(16), rq_vars['order']),
                           params={'order' : rq_vars['order'],
                                   'campaign_uuid' : campaign.uuid,
                                   'user_uuid'     : user.uuid} )
        else:
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
                'supplied_user_id' : rq_vars['uid'],
            }
        else:
            # Make a new Link
            link = create_link(campaign.target_url, campaign, origin_domain, user, rq_vars['uid'])
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
                'FACEBOOK_APP_ID': FACEBOOK_APP_ID,
                'supplied_user_id': rq_vars['uid'],
                'user_email': user_email,
                'user_found': str(user_found).lower()
            }
        
        if self.request.url.startswith('http://localhost'):
            template_values['BASE_URL'] = self.request.url[0:21]
        else:
            template_values['BASE_URL'] = URL
            
        if 'widget' in input_path:
            path = os.path.join(os.path.dirname(__file__), 'html/top.html')
        
        elif 'invite' in input_path:
            template_values['productA_img'] = campaign.shopify_productA_img
            template_values['productB_img'] = campaign.shopify_productB_img
            template_values['productC_img'] = campaign.shopify_productC_img

            path = os.path.join(os.path.dirname(__file__), 'shopify/invite_widget.html')
        
        elif 'bar' in input_path:
            logging.info("BAR: campaign: %s" % (campaign.uuid))
            referrer_cookie = self.request.cookies.get(campaign.uuid, False)
            logging.info('LINK %s' % referrer_cookie)
            referrer_link = get_link_by_willt_code( referrer_cookie )
            if referrer_link:
                template_values['profile_pic']        = referrer_link.user.get_attr( 'pic' )
                template_values['referrer_name']      = referrer_link.user.get_attr( 'full_name' )
                template_values['show_gift']          = True
            self.response.headers['Content-Type'] = 'javascript'
            path = os.path.join(os.path.dirname(__file__), 'js/shopify_bar.js')
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
    
    def get(self, action=''):
        
        service = 'twitter' # hardcoded because we aded the linkedin handler
        rq_vars = get_request_variables(['m', 'wcode'], self)
        user = get_user_by_cookie(self)
        
        if user and getattr(user, 'twitter_access_token', False)\
            and rq_vars.has_key('m') and rq_vars.has_key('wcode'):
            logging.info("tweeting: " + rq_vars['wcode'])
            # tweet and update user model from twitter
            tweet_id, res = user.tweet(rq_vars['m'])
            link = get_link_by_willt_code(rq_vars['wcode'])
            if link:
                link.user = user
                self.response.headers.add_header("Content-type", 'text/javascript')
                if tweet_id is not None:
                    link.tweet_id = tweet_id
                link.save()
                self.response.out.write(res)
            else:
                # TODO: come up with something to do when a link isn't found fo
                #       a message that was /just/ tweeted
                pass 
        else:
            client = OAuthClient(service, self)
            
            if action in client.__public__:
                if action == 'login':
                    logging.info("We didn't recognize you so we're sending you to oauth with your message: " + rq_vars['m'])
                    self.response.out.write(getattr(client, action)(rq_vars['m'],
                                                                    rq_vars['wcode']))
                else:
                    self.response.out.write(getattr(client, action)())
            else:
                self.response.out.write(client.login())
    

class LinkedInOAuthHandler(webapp.RequestHandler):
    
    def get(self, action=''):
        """handles oath requests for linkedin"""
        
        service = 'linkedin' # hardcoded because we aded the linkedin handler
        rq_vars = get_request_variables(['m', 'wcode'], self)
        user = get_user_by_cookie(self)
        
        if user and getattr(user, 'linkedin_access_token', False)\
            and rq_vars.has_key('m') and rq_vars.has_key('wcode'):
            logging.info("LI sharing: " + rq_vars['wcode'])
            
            # share and update user model from linkedin
            linkedin_share_url, res = user.linkedin_share(rq_vars['m'])
            link = get_link_by_willt_code(rq_vars['wcode'])
            if link:
                link.user = user
                self.response.headers.add_header("Content-type", 'text/javascript')
                if linkedin_share_url is not None:
                    link.linkedin_share_url = linkedin_share_url
                link.save()
                self.response.out.write(res)
            else:
                # TODO: come up with something to do when a link isn't found fo
                #       a message that was /just/ tweeted
                pass 
        else:
            client = OAuthClient(service, self)
            
            logging.info('linkedin_access_token %s' % str(getattr(user, 'linkedin_access_token', False)))
            logging.info('user: %s' % user)
            logging.info('rq_vars: %s' % rq_vars)
            
            if action in client.__public__:
                if action == 'login':
                    logging.info("We didn't recognize you so we're sending you to oauth with your message: " + rq_vars['m'])
                    self.response.out.write(
                        getattr(client, action)(rq_vars['m'], rq_vars['wcode'])
                    )
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
        via_willet = True if self.request.get( 'via_willet' ) == 'true' else False
        
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

class FacebookShare(webapp.RequestHandler):
    """This handler attempts to share a status message for a given user
       based on a pre-stored oauth key.
       Responses:
            ok - facebook share successful
            fail - facebook denied post request
            deadlink - link not found
            notfound - user or fb info not found"""
    
    def post(self):
        logging.info("We are posting to facebook")
        rq_vars = get_request_variables(['msg', 'wcode', 'fb_token', 'fb_id']
                                        , self)
        user = get_user_by_cookie(self)
        if user is None:
            logging.info("creating a new user")
            user = get_or_create_user_by_facebook(rq_vars['fb_id'],
                                                  token=rq_vars['fb_token'],
                                                  request_handler=self)
        if hasattr(user, 'facebook_access_token') and hasattr(user, 'fb_identity'):
            facebook_share_id, plugin_response = user.facebook_share(rq_vars['msg'])
            link = get_link_by_willt_code(rq_vars['wcode'])
            if link:
                link = get_link_by_willt_code(rq_vars['wcode'])
                # add the user to the link now as we may not get a respone
                link.add_user(user)
            self.response.out.write(plugin_response)
        else: # no user found
            self.response.out.write('notfound')


def main():
    application = webapp.WSGIApplication([
        (r'/fbShare', FacebookShare),
        (r'/sendEmailInvites', SendEmailInvites),
        (r'/share', DynamicSocialLoader),
        (r'/oauth/twitter/(.*)', TwitterOAuthHandler),
        (r'/oauth/linkedin/(.*)', LinkedInOAuthHandler),
        (r'/(.*)', ServeSharingPlugin)],
        debug=USING_DEV_SERVER)
    run_wsgi_app(application)

if __name__ == "__main__":
    main()

