#!/usr/bin/python

# SIBTShopify model
# Extends from "Referral", which extends from "App"

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc"

import hashlib
import logging
import datetime
import inspect

from django.utils         import simplejson as json
from google.appengine.ext import db
from google.appengine.api import memcache
from google.appengine.datastore import entity_pb
from google.appengine.ext import db

from apps.app.shopify.models import AppShopify
from apps.sibt.models     import SIBT 
from apps.email.models    import Email
from util                 import httplib2
from util.consts          import *
from util.helpers         import generate_uuid
from util.helpers import url as reverse_url

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
        #data = [{
        #    "script_tag": {
        #        "src": "%s/s/shopify/sibt.js?store_id=%s&store_url=%s" % (
        #            URL,
        #            self.store_id,
        #            self.store_url
        #        ),
        #        "event": "onload"
        #    }
        #}]

        script_src = """<!-- START willet sibt for Shopify -->
            <script type="text/javascript">
            (function(window) {
                var hash = window.location.hash;
                var hash_index = hash.indexOf('#code=');
                var willt_code = hash.substring(hash_index + '#code='.length , hash.length);
                var params = "store_url={{ shop.permanent_domain }}&willt_code="+willt_code;
                var src = "//%s%s?" + params;
                var script = window.document.createElement("script");
                script.type = "text/javascript";
                script.src = src;
                window.document.getElementsByTagName("head")[0].appendChild(script);
            }(window));
            </script>
            """ % (DOMAIN, reverse_url('SIBTShopifyServeScript'))
        willet_snippet = script_src + """
            <div id="_willet_shouldIBuyThisButton" data-merchant_name="{{ shop.name | escape }}"
                data-product_id="{{ product.id }}" data-title="{{ product.title | escape  }}"
                data-price="{{ product.price | money }}" data-page_source="product"
                data-image_url="{{ product.images[0] | product_img_url: "large" | replace: '?', '%3F' | replace: '&','%26'}}"></div>
            <!-- END Willet SIBT for Shopify -->"""

        liquid_assets = [{
            'asset': {
                'value': willet_snippet,
                'key': 'snippets/willet_sibt.liquid'
            }
        }]
        # Install yourself in the Shopify store
        self.install_webhooks()
        #self.install_script_tags(script_tags=data)
        self.install_assets(assets=liquid_assets)

        # Email Barbara
        Email.emailBarbara(
            'SIBT Install: %s %s %s' % (
                self.uuid, 
                self.client.name, 
                self.store_url 
            )
        )

        # Fire off "personal" email from Fraser
        Email.welcomeClient( "Should I Buy This", 
                             self.client.merchant.get_attr('email'), 
                             self.client.merchant.get_full_name(), 
                             self.client.name )

    def put(self):
        """So we memcache by the store_url as well"""
        logging.info('enhanced SIBTShopify put')
        super(SIBTShopify, self).put()
        self.memcache_by_store_url()

    def memcache_by_store_url(self):
        return memcache.set(
                self.store_url, 
                db.model_to_protobuf(self).Encode(), time=MEMCACHE_TIMEOUT)
    
    @staticmethod
    def create(client, token):
        uuid = generate_uuid( 16 )
        app = SIBTShopify(
                        key_name    = uuid,
                        uuid        = uuid,
                        client      = client,
                        store_name  = client.name, # Store name
                        store_url   = client.url, # Store url
                        store_id    = client.id, # Store id
                        store_token = token)
        app.put()
        
        app.do_install()
        
        return app

    @staticmethod
    def get_or_create(client, token=None):
        app = SIBTShopify.get_by_store_url(client.url)
        if app is None:
            app = SIBTShopify.create(client, token)
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

    @staticmethod
    def get_by_uuid(uuid):
        return SIBTShopify.get(uuid)

    @staticmethod
    def get_by_store_url(url):
        data = memcache.get(url)
        if data:
            app = db.model_from_protobuf(entity_pb.EntityProto(data))
        else:
            app = SIBTShopify.all()\
                .filter('store_url =', url)\
                .get()
            if app:
                app.memcache_by_store_url()

        return app

    @staticmethod
    def get_by_store_id(store_id):
        logging.info("Shopify: Looking for %s" % store_id)
        logging.warn('THIS METHOD IS DEPRECATED: %s' % inspect.stack()[0][3])
        return SIBTShopify.all()\
                .filter('store_id =', store_id)\
                .get()

# Constructor ------------------------------------------------------------------
def create_sibt_shopify_app(client, token):
    logging.warn('THIS METHOD IS DEPRECATED: %s' % inspect.stack()[0][3])
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
    logging.warn('THIS METHOD IS DEPRECATED: %s' % inspect.stack()[0][3])
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
    logging.warn('THIS METHOD IS DEPRECATED: %s' % inspect.stack()[0][3])
    return SIBTShopify.get(id)
    #return SIBTShopify.all()\
    #        .filter('uuid =', id)\
    #        .get()

def get_sibt_shopify_app_by_store_url(url):
    """ Fetch a Shopify obj from the DB via the store's url"""
    logging.info("Shopify: Looking for %s" % url)
    logging.warn('THIS METHOD IS DEPRECATED: %s' % inspect.stack()[0][3])
    return SIBTShopify.all()\
            .filter('store_url =', url)\
            .get()

def get_sibt_shopify_app_by_store_id(id):
    """ Fetch a Shopify obj from the DB via the store's id"""
    logging.info("Shopify: Looking for %s" % id)
    logging.warn('THIS METHOD IS DEPRECATED: %s' % inspect.stack()[0][3])
    return SIBTShopify.all()\
            .filter('store_id =', id)\
            .get()

