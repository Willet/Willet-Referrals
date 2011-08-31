#!/usr/bin/python

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc."

import hashlib, re

from django.utils import simplejson as json
from gaesessions import get_current_session
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api.datastore_errors import BadValueError

from models.client   import Client
from models.shopify_campaign import get_shopify_campaign_by_id, get_shopify_campaign_by_url, ShopifyCampaign
from models.user     import User, get_user_by_cookie
from util.consts     import *
from util.helpers    import *
from util.urihandler import URIHandler

##-----------------------------------------------------------------------------##
##------------------------- The Shows -----------------------------------------##
##-----------------------------------------------------------------------------##

class ShowShopifyEditPage( URIHandler ):
    # Renders a campaign page
    def get(self):
        # Request varZ from us
        campaign_id  = self.request.get( 'id' )
        error        = self.request.get( 'error' )
        error_msg    = self.request.get( 'error_msg')
        store_name   = self.request.get( 'store_name' )
        store_url    = self.request.get( 'store_url' )
        share_text   = self.request.get( 'share_text' )
        
        # Request varZ from Shopify
        shopify_url  = self.request.get( 'shop' )
        shopify_sig  = self.request.get( 'signature' )
        store_token  = self.request.get( 't' )
        shopify_timestamp = self.request.get( 'timestamp' )
        
        # Init the template values with a blank campaign
        template_values = { 'campaign' : None }
        
        # Check the Shopify stuff if they gave it to us.
        # If it fails, let's just say they aren't coming from Shopify.
        # If we don't have this info, we could be redirecting on an error
        if shopify_url != '':
            s = 'shop=%st=%stimestamp=%s' % (shopify_url, store_token, shopify_timestamp)
            d = hashlib.md5( SHOPIFY_API_SHARED_SECRET + s).hexdigest()
            logging.info('S: %s D: %s' % (shopify_sig, d))
            if shopify_sig == d: # ie. if this is valid from shopify
                              
                # Update the values if this is the first time.
                store_name = shopify_url.split( '.' )[0].capitalize()
  
                # Ensure the 'http' is in the URL
                if 'http' not in shopify_url:
                    shopify_url = 'http://%s' % shopify_url

                url = '%s/admin/shop.json' % ( shopify_url )
                username = SHOPIFY_API_KEY
                password = hashlib.md5(SHOPIFY_API_SHARED_SECRET + store_token).hexdigest()

                # this creates a password manager
                passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
                # because we have put None at the start it will always
                # use this username/password combination for  urls
                # for which `url` is a super-url
                passman.add_password(None, url, username, password)

                # create the AuthHandler
                authhandler = urllib2.HTTPBasicAuthHandler(passman)

                opener = urllib2.build_opener(authhandler)

                # All calls to urllib2.urlopen will now use our handler
                # Make sure not to include the protocol in with the URL, or
                # HTTPPasswordMgrWithDefaultRealm will be very confused.
                # You must (of course) use it when fetching the page though.
                urllib2.install_opener(opener)
                
                # authentication is now handled automatically for us
                logging.info("Querying %s" % url )
                result = urllib2.urlopen(url)
                
                details = json.loads( result.read() ) 
                shop    = details['shop']
                logging.info('shop: %s' % (shop))
                    
                # Update the template
                template_values['shop_owner']  = shop['shop_owner']
                template_values['store_token'] = store_token
                
                campaign = get_shopify_campaign_by_url( shopify_url )
                if campaign is None:
                    logging.info("GOUNF")
                    template_values['campaign']     = { 'store_name' : store_name,
                                                        'store_url'  : shopify_url }
                    template_values['has_campaign'] = False
                else:
                    template_values['campaign'] = campaign

            # The Shopify check failed. Redirecting to normal site. 
            # TODO(Barbara): This might need to change in the future.
            else:
                logging.info("REDIRECTING")
                self.redirect( '/edit' )
                return

        # Fake a campaign to put data in if there is an error
        if error == '1':
            template_values['error'] = 'Invalid Shopify store url.'
            template_values['campaign'] = { 'store_name' : store_name,
                                            'store_url' : store_url,
                                            'share_text' : share_text, 
                                            'store_token' : store_token
                                          }
        elif error == '2':
            template_values['error'] = 'Please don\'t leave anything blank.'
            template_values['campaign'] = { 'store_name' : store_name,
                                            'store_url' : store_url,
                                            'share_text' : share_text, 
                                            'store_token' : store_token
                                          }
        elif error == '3':
            template_values['error'] = 'There was an error with one of your inputs: %s' % error_msg
            template_values['campaign'] = { 'store_name' : store_name,
                                            'store_url' : store_url,
                                            'share_text' : share_text, 
                                            'store_token' : store_token
                                          }

        # If there is no campaign_id, then we are creating a new one:
        elif campaign_id != '':
            
            # Updating an existing campaign here:
            campaign = get_shopify_campaign_by_id( campaign_id )
            if campaign == None:
                self.redirect( '/edit' )
                return
            
            template_values['campaign'] = campaign

        template_values['BASE_URL'] = URL

        self.response.out.write(self.render_page('edit.html', template_values))

class ShowShopifyCodePage( URIHandler ):
    def get(self):
        campaign_id = self.request.get( 'id' )
        template_values = { 'campaign' : None }
        
        if campaign_id:
            # Updating an existing campaign here:
            campaign = get_shopify_campaign_by_id( campaign_id )
            if campaign == None:
                self.redirect( '/account' )
                return

            template_values['campaign'] = campaign
        
        template_values['BASE_URL'] = URL

        self.response.out.write(self.render_page('code.html', template_values))

##-----------------------------------------------------------------------------##
##------------------------- The Dos -------------------------------------------##
##-----------------------------------------------------------------------------##

class DoUpdateOrCreateShopifyCampaign( URIHandler ):
    def post( self ):
        client      = self.get_client() # might be None
        # Request varZ
        campaign_id = self.request.get( 'uuid' )
        store_name  = self.request.get( 'store_name' )
        store_url   = self.request.get( 'store_url' )
        share_text  = self.request.get( 'share_text' )
        store_token = self.request.get( 'token' )
        
        # Error check the input!
        if store_name == '' or store_url == ''  or share_text == '':
            self.redirect( '/shopify/edit?id=%s&t=%s&error=2&share_text=%s&store_url=%s&store_name=%s' % (campaign_id, store_token, share_text, store_url, store_name) )
            return
        if not isGoodURL( store_url ):
            self.redirect( '/shopify/edit?id=%s&t=%s&error=1&share_text=%s&store_url=%s&store_name=%s' % (campaign_id, store_token, share_text, store_url, store_name) )
            return
        
        # Try to grab the ShopifyCampaign
        campaign = get_shopify_campaign_by_id( campaign_id )
        
        # If campaign doesn't exist,
        if campaign == None:
        
            # Create a new one!
            try:
                url = '%s/admin/shop.json' % ( store_url )
                username = SHOPIFY_API_KEY
                password = hashlib.md5(SHOPIFY_API_SHARED_SECRET + store_token).hexdigest()

                # this creates a password manager
                passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
                # because we have put None at the start it will always
                # use this username/password combination for  urls
                # for which `url` is a super-url
                passman.add_password(None, url, username, password)

                # create the AuthHandler
                authhandler = urllib2.HTTPBasicAuthHandler(passman)

                opener = urllib2.build_opener(authhandler)

                # All calls to urllib2.urlopen will now use our handler
                # Make sure not to include the protocol in with the URL, or
                # HTTPPasswordMgrWithDefaultRealm will be very confused.
                # You must (of course) use it when fetching the page though.
                urllib2.install_opener(opener)
                
                # authentication is now handled automatically for us
                logging.info("Querying %s" % url )
                result = urllib2.urlopen(url)
                
                details = json.loads( result.read() ) 
                shop    = details['shop']
                logging.info('shop: %s' % (shop))
                uuid = str(shop['id'])

                # This person probably didn't log in,
                # so make a new Client for them without a passphrase.
                if client is None:
                    client = Client( key_name=shop['email'], uuid=generate_uuid(16), email=shop['email'] )
                    client.put()

                domain = shop['domain']
                if not 'http' in domain:
                    domain = "http://%s" % domain
                campaign = ShopifyCampaign( key_name=uuid,
                                            uuid=uuid,
                                            client=client, 
                                            store_name=shop['name'],
                                            store_url=domain,
                                            share_text=share_text,
                                            store_token=store_token )
                campaign.put()
            except BadValueError, e:
                self.redirect( '/shopify/edit?error=3&error_msg=%s&id=%s&t=%s&share_text=%s&store_url=%s&store_name=%s' % (str(e), campaign_id, store_token, share_text, store_url, store_name) )
                return
        
        # Otherwise, update the existing campaign.
        else:
            try:
                campaign.update( store_name = store_name,
                                 store_url  = store_url,
                                 share_text = share_text )
            except BadValueError, e:
                self.redirect( '/shopify/edit?error=3&error_msg=%s&id=%s&t=%s&share_text=%s&store_url=%s&store_name=%s' % (str(e), campaign_id, store_token, share_text, store_url, store_name) )
                return
        
        self.redirect( '/shopify/r/code?id=%s' % campaign.uuid )

##-----------------------------------------------------------------------------##
##------------------------- The URI Router ------------------------------------##
##-----------------------------------------------------------------------------##
def main():
    application = webapp.WSGIApplication([
        (r'/shopify/r/code', ShowShopifyCodePage),
        (r'/shopify/r/edit', ShowShopifyEditPage),
        
        (r'/shopify/doUpdateOrCreateCampaign', DoUpdateOrCreateShopifyCampaign),
        
        ], debug=USING_DEV_SERVER)
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
