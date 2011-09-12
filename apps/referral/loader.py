#!/usr/bin/python

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc."

import hashlib, re

from django.utils import simplejson as json
from gaesessions import get_current_session
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api.datastore_errors import BadValueError
from google.appengine.api import taskqueue, urlfetch
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

from models.client   import Client, get_client_by_email, authenticate, register
from models.shopify_campaign import get_shopify_campaign_by_id, ShopifyCampaign
from models.link     import create_link, Link, get_link_by_willt_code
from models.shopify_order  import ShopifyItem, create_shopify_order, get_shopify_order_by_token
from models.stats    import Stats
from models.user     import User, get_or_create_user_by_cookie
from util.helpers    import *
from util.urihandler import URIHandler
from util.consts     import *

class DynamicLoader(webapp.RequestHandler):
    """When requested serves a plugin that will contain various functionality
       for sharing information about a purchase just made by one of our clients"""
    
    def get(self, input_path):
        logging.info('Token %s' % self.request.get('order_token'))
        template_values = {}
        rq_vars = get_request_variables(['store_id', 'order_token'], self)
        origin_domain = os.environ['HTTP_REFERER'] if\
            os.environ.has_key('HTTP_REFERER') else 'UNKNOWN'
        
        # Grab a User if we have a cookie!
        user = get_or_create_user_by_cookie(self)
        user_email = user.get_attr('email') if user else ""
        user_found = True if hasattr(user, 'fb_access_token') else False
        
        campaign = get_shopify_campaign_by_id( rq_vars['store_id'] )
        
        # If they give a bogus campaign id, show the landing page campaign!
        logging.info(campaign)
        if campaign == None:
            template_values = {
                'NAME' : NAME,
                
                'text': "",
                'willt_url' : URL,
                'willt_code': "",
                'campaign_uuid' : "",
                'store_url' : URL,
                
                'user' : user,
                'user_email' : user_email
            }
        else:
            # Make a new Link
            link = create_link(campaign.store_url, campaign, origin_domain, user)
            logging.info("link created is %s" % link.willt_url_code)

            # Fetch the Shopify Order
            order = get_shopify_order_by_token( rq_vars['order_token'] )

            # Create the share text
            if campaign.store_url in campaign.share_text:
                share_text = campaign.share_text.replace( campaign.store_url, link.get_willt_url() )
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
                'order_id': order.order_id if order else "",
                
                'user': user,
                'FACEBOOK_APP_ID': FACEBOOK_APP_ID,
                'user_email': user_email,
                'user_found': str(user_found).lower()
            }
        
        if self.request.url.startswith('http://localhost'):
            template_values['BASE_URL'] = self.request.url[0:21]
        else:
            template_values['BASE_URL'] = URL
            
        if 'referral' in input_path:
            path = os.path.join(os.path.dirname(__file__), 'templates/referral_plugin.html')
        
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
            path = os.path.join(os.path.dirname(__file__), 'templates/referral_top_bar.js')
        
        logging.info("rendeirng %s" % path)
        self.response.out.write(template.render(path, template_values))

        return

##-----------------------------------------------------------------------------##
##------------------------- The URI Router ------------------------------------##
##-----------------------------------------------------------------------------##
def main():
    application = webapp.WSGIApplication([
        (r'/shopify/load/(.*)', DynamicLoader),
        ], debug=USING_DEV_SERVER)
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
