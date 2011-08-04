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
from models.link import create_link
from models.oauth import OAuthClient

# helpers
from util.consts import *

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
        
        client = OAuthClient(service, self)

        if action in client.__public__:
            self.response.out.write(getattr(client, action)())
        else:
            self.response.out.write(client.login())

def main():
    application = webapp.WSGIApplication([
        (r'/share', DynamicSocialLoader),
        (r'/oauth/(.*)/(.*)', TwitterOAuthHandler),
        (r'/willt', ServeSharingPlugin)],
        debug=USING_DEV_SERVER)
    run_wsgi_app(application)

if __name__ == "__main__":
    main()

