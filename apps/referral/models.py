#!/usr/bin/python

# Referral model
# Extends from "App"

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc"

import hashlib, logging, datetime

from django.utils         import simplejson as json
from google.appengine.ext import db

from util.app             import App
from util.consts          import *

# ------------------------------------------------------------------------------
# Referral Class Definition ---------------------------------------------
# ------------------------------------------------------------------------------
class Referral( App ):
    """Model storing the data for a client's sharing app"""
    emailed_at_10 = db.BooleanProperty( default = False )
   
    product_name  = db.StringProperty( indexed = True )
    target_url    = db.LinkProperty  ( indexed = False )
    
    share_text    = db.StringProperty( indexed = False )
    webhook_url   = db.LinkProperty( indexed = False, default = None, required = False )

    def __init__(self, *args, **kwargs):
        """ Initialize this model """
        super(Referral, self).__init__(*args, **kwargs)
    
    def update( self, title, product_name, target_url, share_text, webhook_url ):
        """Update the app with new data"""
        self.title        = title
        self.product_name = product_name
        self.target_url   = target_url
        
        self.share_text   = share_text

        self.webhook_url  = webhook_url
        self.put()

# Accessors --------------------------------------------------------------------
def get_referral_app_by_url( url ):
    """ Fetch a Referral obj from the DB via the url """
    logging.info("Referral: Looking for %s" % url )
    return Referral.all().filter( 'target_url =', url ).get()


# ------------------------------------------------------------------------------
# ReferralShopify Class Definition ---------------------------------------------
# ------------------------------------------------------------------------------
class ReferralShopify( Referral ):
    
    def __init__(self, *args, **kwargs):
        """ Initialize this model """

        # Install yourself in the Shopify store
        install_webhooks( kwargs['store_url'], kwargs['store_token'] )
        install_script_tags( kwargs['store_url'], kwargs['store_token'] )
        
        super(ReferralShopify, self).__init__(*args, **kwargs)
    
# Shopify API Calls ------------------------------------------------------------
def install_webhooks( store_url, store_token ):
    """ Install the webhooks into the Shopify store """

    url      = '%s/admin/webhooks.json' % ( store_url )
    username = SHOPIFY_API_KEY
    password = hashlib.md5(SHOPIFY_API_SHARED_SECRET + store_token).hexdigest()
    header   = {'content-type':'application/json'}
    h        = httplib2.Http()
    
    # Auth the http lib
    h.add_credentials( username, password )
    
    # Install the "Order Creation" webhook
    data = { "webhook": { "address": "%s/shopify/webhook/order?store_id=%s" % (URL, referralApp.uuid), "format": "json", "topic": "orders/create" } }
    logging.info("POSTING to %s %r " % (url, data) )
    resp, content = h.request(url, "POST", body=json.dumps(data), headers=header)
    logging.info('%r %r' % (resp, content))

    # Install the "App Uninstall" webhook
    data = { "webhook": { "address": "%s/shopify/webhook/uninstalled" % URL, "format": "json", "topic": "app/uninstalled" } }
    logging.info("POSTING to %s %r " % (url, data) )
    resp, content = h.request(url, "POST", body=json.dumps(data), headers=header)
    logging.info('%r %r' % (resp, content))
    
def install_script_tags( store_url, store_token ):
    """ Install our script tags onto the Shopify store """

    url      = '%s/admin/script_tags.json' % ( store_url )
    username = SHOPIFY_API_KEY
    password = hashlib.md5(SHOPIFY_API_SHARED_SECRET + store_token).hexdigest()
    header   = {'content-type':'application/json'}
    h        = httplib2.Http()
    
    h.add_credentials( username, password )

    # Install the referral plugin on confirmation screen
    data = { "script_tag": { "src": "https://social-referral.appspot.com/static/referral/js/shopify.js", "event": "onload" } }      

    logging.info("POSTING to %s %r " % (url, data) )
    resp, content = h.request(url, "POST", body=json.dumps(data), headers=header)
    logging.info('%r %r' % (resp, content))

    # Install jquery cookies
    data = { "script_tag": { "src": "http://social-referral.appspot.com/static/js/jquery.cookie.js", "event": "onload" } }      
    
    logging.info("POSTING to %s %r " % (url, data) )
    resp, content = h.request(url, "POST", body=json.dumps(data), headers=header)
    logging.info('%r %r' % (resp, content))

    # Install the top_bar JS 
    data = { "script_tag": { "src": "http://social-referral.appspot.com/shopify/load/bar?store_id=%s" % (referralApp.uuid), "event": "onload" } }      
    
    logging.info("POSTING to %s %r " % (url, data) )
    resp, content = h.request(url, "POST", body=json.dumps(data), headers=header)
    logging.info('%r %r' % (resp, content))
