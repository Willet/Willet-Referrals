#!/usr/bin/python

# SIBTShopify model
# Extends from "Referral", which extends from "App"

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc"

import hashlib, logging, datetime

from django.utils         import simplejson as json
from google.appengine.ext import db

from apps.app.shopify.models import AppShopify
from apps.sibt.models     import SIBT 
from apps.email.models    import Email
from util                 import httplib2
from util.consts          import *
from util.helpers         import generate_uuid

# ------------------------------------------------------------------------------
# SIBTShopify Class Definition -------------------------------------------------
# ------------------------------------------------------------------------------
class SIBTShopify(SIBT, AppShopify):
    
    # Shopify's ID for this store
    #store_id    = db.StringProperty( indexed = True )

    # Shopify's token for this store
    #store_token = db.StringProperty( indexed = True )

    def __init__(self, *args, **kwargs):
        """ Initialize this model """
        super(SIBTShopify, self).__init__(*args, **kwargs)
    
    def do_install(self):
        """Installs this instance"""
        data = [{
            "script_tag": {
                "src": "%s/s/shopify/sibt.js?store_id=%s&store_url=%s" % (
                    URL,
                    self.store_id,
                    self.store_url
                ),
                "event": "onload"
            }
        }]
        # Install yourself in the Shopify store
        self.install_webhooks()
        self.install_script_tags(script_tags=data)

        # Email Barbara
        Email.emailBarbara(
            'SIBT Install: %s %s %s' % (
                self.uuid, 
                self.client.name, 
                self.store_url 
            )
        )

# Constructor ------------------------------------------------------------------
def create_sibt_shopify_app(client, token):

    uuid = generate_uuid( 16 )
    app = SIBTShopify( key_name    = uuid,
                       uuid        = uuid,
                       client      = client,
                       store_name  = client.name, # Store name
                       store_url   = client.url, # Store url
                       store_id    = client.id, # Store id
                       store_token = token )
    app.put()
    
    app.do_install()
     
    return app

# Accessors --------------------------------------------------------------------
def get_or_create_sibt_shopify_app(client, token=None):
    #app = get_sibt_shopify_app_by_store_id( client.id )
    app = get_sibt_shopify_app_by_store_url(client.url)
    if app is None:
        app = create_sibt_shopify_app(client, token)
    elif token != None and token != '':
        if app.store_token != token:
            # TOKEN mis match, this might be a re-install
            logging.warn(
                'We are going to reinstall this app because the stored token \
                does not match the request token\n%s vs %s' % (
                    app.store_token,
                    token
                )
            ) 
            try:
                app.store_token = token
                app.put()
                app.do_install()
            except:
                logging.error('encountered error with reinstall', exc_info=True)
    return app

def get_sibt_shopify_app_by_uuid(id):
    """ Fetch a Shopify obj from the DB via the uuid"""
    logging.info("Shopify: Looking for %s" % id)
    return SIBTShopify.get(id)
    #return SIBTShopify.all()\
    #        .filter('uuid =', id)\
    #        .get()

def get_sibt_shopify_app_by_store_url(url):
    """ Fetch a Shopify obj from the DB via the store's url"""
    logging.info("Shopify: Looking for %s" % url)
    return SIBTShopify.all()\
            .filter('store_url =', url)\
            .get()

def get_sibt_shopify_app_by_store_id(id):
    """ Fetch a Shopify obj from the DB via the store's id"""
    # TODO: DEPRECATE THIS METHOD
    logging.info("Shopify: Looking for %s" % id)
    return SIBTShopify.all()\
            .filter('store_id =', id)\
            .get()

# Shopify API Calls ------------------------------------------------------------
#def install_webhooks( store_url, store_token ):
#    """ Install the webhooks into the Shopify store """
#
#    logging.info("TOKEN %s" % store_token )
#
#    url      = '%s/admin/webhooks.json' % ( store_url )
#    username = SIBT_SHOPIFY_API_KEY
#    password = hashlib.md5(SIBT_SHOPIFY_API_SHARED_SECRET + store_token).hexdigest()
#    header   = {'content-type':'application/json'}
#    h        = httplib2.Http()
#    
#    # Auth the http lib
#    h.add_credentials( username, password )
#    
#    # Install the "App Uninstall" webhook
#    data = { "webhook": { "address": "%s/r/shopify/webhook/uninstalled" % URL, "format": "json", "topic": "app/uninstalled" } }
#    logging.info("POSTING to %s %r " % (url, data) )
#    resp, content = h.request(url, "POST", body=json.dumps(data), headers=header)
#    logging.info('%r %r' % (resp, content))
#
#    if int(resp.status) == 401:
#        Email.emailBarbara(
#            'SIBT WEBHOOK INSTALL FAILED\n%s\n%s' % (
#                resp,
#                content
#            )        
#        )
#    
#def install_script_tags( store_url, store_token, store_id ):
#    """ Install our script tags onto the Shopify store """
#
#    url      = '%s/admin/script_tags.json' % ( store_url )
#    username = SIBT_SHOPIFY_API_KEY
#    password = hashlib.md5(SIBT_SHOPIFY_API_SHARED_SECRET + store_token).hexdigest()
#    header   = {'content-type':'application/json'}
#    h        = httplib2.Http()
#    
#    h.add_credentials( username, password )
#     
#    # Install the SIBT script
#    data = { "script_tag": { "src": "%s/s/shopify/sibt.js?store_id=%s" % (URL, store_id), "event": "onload" } }      
#
#    logging.info("POSTING to %s %r " % (url, data) )
#    resp, content = h.request(url, "POST", body=json.dumps(data), headers=header)
#    logging.info('%r %r' % (resp, content))
#
#    if int(resp.status) == 401:
#        Email.emailBarbara(
#            'SIBT WEBHOOK INSTALL FAILED\n%s\n%s' % (
#                resp,
#                content
#            )        
#        )

