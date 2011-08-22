#!/usr/bin/python

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc."

import hashlib, re

from django.utils import simplejson as json
from gaesessions import get_current_session
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api.datastore_errors import BadValueError

from models.client   import Client, get_client_by_email, authenticate, register
from models.campaign import get_campaign_by_id, Campaign
from models.feedback import Feedback
from models.stats    import Stats
from models.user     import User, get_user_by_cookie
from util.helpers    import *
from util.urihandler import URIHandler
from util.consts     import *

##-----------------------------------------------------------------------------##
##------------------------- The Shows -----------------------------------------##
##-----------------------------------------------------------------------------##

class ShowShopifyEditPage( URIHandler ):
    # Renders a campaign page
    def get(self):
        campaign_id  = self.request.get( 'id' )
        error        = self.request.get( 'error' )
        error_msg    = self.request.get( 'error_msg')
        product_name = self.request.get( 'product_name' )
        target_url   = self.request.get( 'target_url' )
        share_text   = self.request.get( 'share_text' )
        
        shopify_url = self.request.get( 'shop' )
        shopify_sig = self.request.get( 'signature' )
        shopify_token = self.request.get( 't' )
        shopify_timestamp = self.request.get( 'timestamp' )
        
        template_values = { 'campaign' : None }
        
        # Check the Shopify stuff if they gave it to us
        # If it failed, let's just say they aren't coming from Shopify
        if shopify_url != '':
            s = 'shop=%st=%stimestamp=%s' % (shopify_url, shopify_token, shopify_timestamp)
            d = hashlib.md5( SHOPIFY_API_SHARED_SECRET + s).hexdigest()
            logging.info('S: %s D: %s' % (shopify_sig, d))
            if shopify_sig == d: # ie. if this is valid from shopify
                              
                # Update the values if this is the first time.
                product_name = shopify_url.split( '.' )[0].capitalize()
  
                # Ensure the 'http' is in the URL
                if 'http' not in shopify_url:
                    shopify_url = 'http://%s' % shopify_url

                # Update the template
                template_values['campaign'] = { 'product_name' : product_name,
                                                'target_url'   : shopify_url }

                template_values['shopify_token']  = shopify_token

            else:
                self.redirect( '/edit' )
                return

        # Fake a campaign to put data in if there is an error

        if error == '1':
            template_values['error'] = 'Invalid Shopify store url.'
            template_values['campaign'] = { 'product_name' : product_name,
                                            'target_url' : target_url,
                                            'share_text' : share_text, 
                                            'shopify_token' : shopify_token
                                          }
        elif error == '2':
            template_values['error'] = 'Please don\'t leave anything blank.'
            template_values['campaign'] = { 'product_name' : product_name,
                                            'target_url' : target_url,
                                            'share_text' : share_text, 
                                            'shopify_token' : shopify_token
                                          }
        elif error == '3':
            template_values['error'] = 'There was an error with one of your inputs: %s' % error_msg
            template_values['campaign'] = { 'product_name' : product_name,
                                            'target_url' : target_url,
                                            'share_text' : share_text, 
                                            'shopify_token' : shopify_token
                                          }

        # If there is no campaign_id, then we are creating a new one:
        elif campaign_id:
            
            # Updating an existing campaign here:
            campaign = get_campaign_by_id( campaign_id )
            if campaign == None:
                self.redirect( '/edit' )
                return
            
            template_values['campaign'] = campaign
        
        template_values['BASE_URL'] = URL

        self.response.out.write(self.render_page('shopify_edit.html', template_values))

class ShowShopifyCodePage( URIHandler ):
    def get(self):
        campaign_id = self.request.get( 'id' )
        template_values = { 'campaign' : None }
        
        if campaign_id:
            # Updating an existing campaign here:
            campaign = get_campaign_by_id( campaign_id )
            if campaign == None:
                self.redirect( '/account' )
                return

            template_values['campaign'] = campaign
        
        template_values['BASE_URL'] = URL

        self.response.out.write(self.render_page('shopify_code.html', template_values))

##-----------------------------------------------------------------------------##
##------------------------- The Dos -------------------------------------------##
##-----------------------------------------------------------------------------##

class DoShopifyUpdateOrCreateCampaign( URIHandler ):
    def post( self ):
        client = self.get_client() # might be None

        campaign_id  = self.request.get( 'uuid' )
        product_name = self.request.get( 'product_name' )
        target_url   = self.request.get( 'target_url' )
        share_text   = self.request.get( 'share_text' )
        shopify_token = self.request.get( 'token' )
        
        campaign = get_campaign_by_id( campaign_id )
        
        if product_name == '' or target_url == ''  or share_text == '':
            self.redirect( '/shopify/edit?id=%s&t=%s&error=2&share_text=%s&target_url=%s&product_name=%s' % (campaign_id, shopify_token, share_text, target_url, product_name) )
            return
        
        if not isGoodURL( target_url ):
            self.redirect( '/shopify/edit?id=%s&t=%s&error=1&share_text=%s&target_url=%s&product_name=%s' % (campaign_id, shopify_token, share_text, target_url, product_name) )
            return

        # If campaign doesn't exist,
        if campaign == None:
        
            # Create a new one!
            try:
                uuid = generate_uuid(16)
                campaign = Campaign( key_name=uuid,
                                     uuid=uuid,
                                     client=client, 
                                     title='',
                                     product_name=product_name,
                                     target_url=target_url,
                                     blurb_title='',
                                     blurb_text='',
                                     share_text=share_text,
                                     shopify_token=shopify_token)
                campaign.put()
            except BadValueError, e:
                self.redirect( '/shopify/edit?error=3&error_msg=%s&id=%s&t=%s&share_text=%s&target_url=%s&product_name=%s' % (str(e), campaign_id, shopify_token, share_text, target_url, product_name) )
                return
        
        # Otherwise, update the existing campaign.
        else:
            try:
                campaign.update( title='',
                                 product_name=product_name,
                                 target_url=target_url,
                                 blurb_title='',
                                 blurb_text='',
                                 share_text=share_text,
                                 webhook_url=None)
            except BadValueError, e:
                self.redirect( '/shopify/edit?error=3&error_msg=%s&id=%s&t=%s&share_text=%s&target_url=%s&product_name=%s' % (str(e), campaign_id, shopify_token, share_text, target_url, product_name) )
                return
        
        self.redirect( '/shopify/code?id=%s' % campaign.uuid )

##-----------------------------------------------------------------------------##
##------------------------- The URI Router ------------------------------------##
##-----------------------------------------------------------------------------##
def main():
    application = webapp.WSGIApplication([
        (r'/shopify/code', ShowShopifyCodePage),
        (r'/shopify/edit', ShowShopifyEditPage),
        
        (r'/shopify/doUpdateOrCreateCampaign', DoShopifyUpdateOrCreateCampaign),
        
        ], debug=USING_DEV_SERVER)
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
