#!/usr/bin/python

# ReferralShopify model
# Extends from "Referral", which extends from "App"

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc"

import hashlib, logging, datetime

from django.utils         import simplejson as json
from google.appengine.ext import db

from apps.referral.models import Referral
from util                 import httplib2
from util.consts          import *
from util.helpers         import generate_uuid

# ------------------------------------------------------------------------------
# ReferralShopify Class Definition ---------------------------------------------
# ------------------------------------------------------------------------------
class ReferralShopify( Referral ):
    
    # Shopify's ID for this store
    store_id = db.StringProperty( indexed = True )

    # Shopify's token for this store
    store_token = db.StringProperty( indexed = True )

    def __init__(self, *args, **kwargs):
        """ Initialize this model """
        super(ReferralShopify, self).__init__(*args, **kwargs)

# Constructor ------------------------------------------------------------------
def create_referral_shopify_app( client, share_text ):

    uuid = generate_uuid( 16 )
    app = ReferralShopify( key_name     = uuid,
                           uuid         = uuid,
                           client       = client,
                           product_name = client.name, # Store name
                           target_url   = client.url, # Store url
                           store_id     = client.id, # Store id
                           store_token  = client.token,
                           webhook_url  = None, # Don't need one
                           share_text   = share_text )
    app.put()
    
    # Install yourself in the Shopify store
    install_webhooks( client.url, client.token )
    install_script_tags( client.url, client.token, client.id )
    
    return app

# Accessors --------------------------------------------------------------------
def get_shopify_app_by_uuid(id):
    """ Fetch a Shopify obj from the DB via the uuid"""
    logging.info("Shopify: Looking for %s" % id)
    return ReferralShopify.all().filter( 'uuid =', id ).get()

def get_shopify_app_by_store_id(id):
    """ Fetch a Shopify obj from the DB via the store's id"""
    logging.info("Shopify: Looking for %s" % id)
    return ReferralShopify.all().filter( 'store_id =', id ).get()

# Shopify API Calls ------------------------------------------------------------
def install_webhooks( store_url, store_token ):
    """ Install the webhooks into the Shopify store """

    logging.info("TOKEN %s" % store_token )

    url      = '%s/admin/webhooks.json' % ( store_url )

    # TODO: replace this.
    #username = SHOPIFY_APPS['ReferralShopify']['api_key'] 
    #password = hashlib.md5(SHOPIFY_APPS['ReferralShopify']['api_secret'] + self.store_token).hexdigest()

    username = REFERRAL_SHOPIFY_API_KEY
    password = hashlib.md5(REFERRAL_SHOPIFY_API_SHARED_SECRET + store_token).hexdigest()
    header   = {'content-type':'application/json'}
    h        = httplib2.Http()
    
    # Auth the http lib
    h.add_credentials( username, password )
    
    # Install the "Order Creation" webhook
    data = { "webhook": { "address": "%s/r/shopify/webhook/order" % (URL), "format": "json", "topic": "orders/create" } }
    logging.info("POSTING to %s %r " % (url, data) )
    resp, content = h.request(url, "POST", body=json.dumps(data), headers=header)
    logging.info('%r %r' % (resp, content))

    # Install the "App Uninstall" webhook
    data = { "webhook": { "address": "%s/r/shopify/webhook/uninstalled" % URL, "format": "json", "topic": "app/uninstalled" } }
    logging.info("POSTING to %s %r " % (url, data) )
    resp, content = h.request(url, "POST", body=json.dumps(data), headers=header)
    logging.info('%r %r' % (resp, content))
    
def install_script_tags( store_url, store_token, store_id ):
    """ Install our script tags onto the Shopify store """

    url      = '%s/admin/script_tags.json' % ( store_url )
    username = REFERRAL_SHOPIFY_API_KEY
    password = hashlib.md5(REFERRAL_SHOPIFY_API_SHARED_SECRET + store_token).hexdigest()
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
    data = { "script_tag": { "src": "http://social-referral.appspot.com/r/shopify/load/bar?store_id=%s" % (store_id), "event": "onload" } }      
    
    logging.info("POSTING to %s %r " % (url, data) )
    resp, content = h.request(url, "POST", body=json.dumps(data), headers=header)
    logging.info('%r %r' % (resp, content))
