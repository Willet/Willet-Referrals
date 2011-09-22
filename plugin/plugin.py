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
from apps.app.models import get_app_by_id, App
from apps.link.models import create_link, get_link_by_willt_code
from apps.oauth.models import OAuthClient
from apps.referral.shopify.models import ReferralShopify
from apps.testimonial.models import create_testimonial
from apps.user.models import get_user_by_cookie, get_or_create_user_by_email, get_or_create_user_by_facebook, get_user_by_uuid, get_or_create_user_by_cookie
from apps.email.models import Email

# helpers
from apps.referral.shopify.api_wrapper import add_referrer_gift_to_shopify_order
from util.consts import *
from util.helpers import read_user_cookie, generate_uuid, get_request_variables

class ServeSharingPlugin(webapp.RequestHandler):
    """When requested serves a plugin that will contain various functionality
       for sharing information about a purchase just made by one of our clients"""
    
    def get(self, input_path):
        logging.info(os.environ['HTTP_HOST'])
        logging.info(URL)
        template_values = {}
        rq_vars = get_request_variables(['app_id', 'uid'], self)
        origin_domain = os.environ['HTTP_REFERER'] if\
            os.environ.has_key('HTTP_REFERER') else 'UNKNOWN'
        
        # Grab a User if we have a cookie!
        user = get_or_create_user_by_cookie(self)
        user_email = user.get_attr('email') if user and\
            user.get_attr('email') != '' else "Your Email"
        user_found = True if hasattr(user, 'fb_access_token') else False
        
        app = get_app_by_id(rq_vars['app_id']) 
        p = 5
        

        # If they give a bogus app_id, show the landing page app!
        logging.info(app)
        if app == None:
            template_values = {
                'NAME' : NAME,
                
                'text': "",
                'willt_url' : URL,
                'willt_code': "",
                'app_uuid' : "",
                'target_url' : URL,
                
                'user' : user,
                'user_email' : user_email,
                'supplied_user_id' : rq_vars['uid'],
            }
        else:
            # Make a new Link
            link = create_link(app.target_url, app, origin_domain, user, rq_vars['uid'])
            logging.info("link created is %s" % link.willt_url_code)
            
            # Create the share text
            if app.target_url in app.share_text:
                share_text = app.share_text.replace( app.target_url, link.get_willt_url() )
            else:
                share_text = app.share_text + " " + link.get_willt_url()
            
            template_values = {
                'URL' : URL,
                'NAME' : NAME,
                
                'app' : app,
                'app_uuid' : app.uuid,
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
        else:
            path = os.path.join(os.path.dirname(__file__), 'html/bottom.html')
        
        self.response.out.write(template.render(path, template_values))
        return
    

class DynamicSocialLoader(webapp.RequestHandler):
    """Dynamically loads the source of an iframe containing a app's
       share text. Currently supports: tweet, facebook share, email"""
    
    def get(self):
        template_values = {}
        app_id = self.request.get('app_id')
        user_id = self.request.get('uid')
        social_type = self.request.get('type')
        origin_domain = os.environ['HTTP_REFERER'] if\
            os.environ.has_key('HTTP_REFERER') else 'UNKNOWN'
            
        if self.request.url.startswith('http://localhost:8080'):
            template_values['BASE_URL'] = self.request.url[0:21]
            
        app = get_app_by_id(app_id)
        
        # If they give a bogus app id, show the landing page app!
        if app == None:
            template_values = {
                'text': "",
                'willt_url' : URL,
                'willt_code': "",
                'app_uuid' : "",
                'target_url' : URL
            }
        else:
            link = create_link(app.target_url, app, origin_domain, user_id)
            logging.info("link created is %s" % link.willt_url_code)
            
            if app.target_url in app.share_text:
                share_text = app.share_text.replace( app.target_url, link.get_willt_url() )
            else:
                share_text = app.share_text + " " + link.get_willt_url()
                
            template_values = {
                'text': share_text.replace("\"", "'"),
                'willt_url' : link.get_willt_url(),
                'willt_code': link.willt_url_code,
                'app_uuid' : app.uuid,
                'target_url' : app.target_url,
                'redirect_url' : app.redirect_url if app.redirect_url else "",
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
        rq_vars = get_request_variables(['m', 'wcode', 'order_id'], self)
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
                    link.app_.increment_shares()
                link.save()
                self.response.out.write(res)
            
            # If we are on a shopify store, add a gift to the order
            if link.app_.__class__.__name__.lower() == 'referralshopify':
                add_referrer_gift_to_shopify_order( rq_vars['order_id'] )
            
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
        rq_vars = get_request_variables(['m', 'wcode', 'order_id'], self)
        user = get_user_by_cookie(self)
        
        if user and getattr(user, 'linkedin_access_token', False)\
            and rq_vars.has_key('m') and rq_vars.has_key('wcode'):
            logging.info("LI sharing: " + rq_vars['wcode'])
            
            # share and update user model from linkedin
            linkedin_share_url, res = user.linkedin_share(rq_vars['m'])

            # If we are on a shopify store, add a gift to the order
            if link.app_.__class__.__name__.lower() == 'referralapp':
                add_referrer_gift_to_shopify_order( rq_vars['order_id'] )

            link = get_link_by_willt_code(rq_vars['wcode'])
            if link:
                create_testimonial(user, rq_vars['m'], link) 
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
        order_id  = self.request.get( 'order_id' ) 
        willt_url_code = self.request.get( 'willt_url_code' )
        via_willet = True if self.request.get( 'via_willet' ) == 'true' else False
        
        logging.info("ASDSD %s %s %s" % (self.request.arguments(),willt_url_code, order_id))

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
            link.email_sent = True
            link.put()
            
            for i in range(0, to_addrs.count(',')):
                link.app_.increment_shares()
                
        # Save this Testimonial
        create_testimonial(user=user, message=msg, link=link)

        # If we are on a shopify store, add a gift to the order
        if link.app_.__class__.__name__.lower() == 'referralshopify':
            add_referrer_gift_to_shopify_order( order_id )

        # Send off the email if they don't want to use a webmail client
        if via_willet and to_addrs != '':
            Email.invite( infrom_addr=from_addr, to_addrs=to_addrs, msg=msg, url=url, app=link.app_)

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
        rq_vars = get_request_variables([
            'msg',
            'wcode',
            'fb_token',
            'fb_id',
            'order_id',
            'img'], 
            self
        )
        user = get_user_by_cookie(self)
        if user is None:
            logging.info("creating a new user")
            user = get_or_create_user_by_facebook(
                rq_vars['fb_id'],
                token=rq_vars['fb_token'],
                request_handler=self
            )
        elif hasattr(user, 'fb_access_token') and hasattr(user, 'fb_identity'):
            # if the user already exists and has both
            # a fb access token and id, let's check to make sure
            # it is the same info as we just got
            if user.fb_access_token != rq_vars['fb_token'] or\
                    user.fb_identity != rq_vars['fb_id']:
                logging.error('existing users facebook information did not\
                    match new data. overwriting old data!')
                logging.error('user: %s' % user)
                #user.update(
                #    fb_identity=rq_vars['fb_id'],
                #    fb_access_token=rq_vars['fb_token']
                #)
        else:
            # got an existing user both doesn't have 
            # facebook info
            user.update(
                fb_identity = rq_vars['fb_id'],
                fb_access_token = rq_vars['fb_token']
            )

        if hasattr(user, 'fb_access_token') and hasattr(user, 'fb_identity'):
            logging.info('got user and have facebook jazz')

            facebook_share_id, plugin_response = user.facebook_share(rq_vars['msg'], rq_vars['img'])
            link = get_link_by_willt_code(rq_vars['wcode'])
            if link:
                link = get_link_by_willt_code(rq_vars['wcode'])
                link.app_.increment_shares()
                # add the user to the link now as we may not get a respone
                link.add_user(user)

                # Save the Testimonial
                create_testimonial(user=user, message=rq_vars['msg'], link=link)

                # If we are on a shopify store, add a gift to the order
                if link.app_.__class__.__name__.lower() == 'referralshopify':
                    add_referrer_gift_to_shopify_order( rq_vars['order_id'] )
            else:
                logging.error('could not get link')
            logging.info('sending response %s' % plugin_response)
            self.response.out.write(plugin_response)
        else: # no user found
            logging.error('user facebook info not found')
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

