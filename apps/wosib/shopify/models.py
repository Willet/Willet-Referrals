#!/usr/bin/python

# WOSIBShopify model
# Extends from "Referral", which extends from "App"

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2012, Willet, Inc"

import hashlib
import logging
import datetime
import inspect

from django.utils         import simplejson as json
from google.appengine.ext import db
from google.appengine.api import memcache
from google.appengine.datastore import entity_pb
from google.appengine.ext.webapp import template

from apps.app.shopify.models import AppShopify
from apps.client.models     import Client
from apps.wosib.models     import WOSIB 
from apps.email.models    import Email
from apps.user.models import get_user_by_cookie
from util                 import httplib2
from util.consts          import *
from util.helpers         import generate_uuid
from util.helpers import url as reverse_url

# ------------------------------------------------------------------------------
# WOSIBShopify Class Definition -------------------------------------------------
# ------------------------------------------------------------------------------
class WOSIBShopify(WOSIB, AppShopify):
    
    # Shopify's ID for this store
    #store_id    = db.StringProperty( indexed = True )
    
    def __init__(self, *args, **kwargs):
        """ Initialize this model """
        super(WOSIBShopify, self).__init__(*args, **kwargs)
    
    def do_install(self):
        # "You must escape a percent sign with another percent sign." TIL.
        """Installs this instance"""
        script_src = '''<!-- START willet wosib for Shopify -->
            <script type="text/javascript">
                if (typeof jQuery == 'undefined' || jQuery.fn.jquery < "1.6.0"){ // if page has no jQuery, load from CDN; apparently, string version comparison works even if its casted value has two decimal points.
                    document.write(unescape("%%3Cscript src='http://ajax.googleapis.com/ajax/libs/jquery/1.6.2/jquery.min.js' type='text/javascript' %%3E%%3C/script%%3E"));
                }
                if (typeof jQuery == 'undefined'){ // if it is STILL undefined, load our own
                    document.write(unescape("%%3Cscript src='/static/js/jquery.min.js' type='text/javascript' %%3E%%3C/script%%3E"));
                }
                var _willet_no_image = "http://%s/static/imgs/noimage.png";
                var _willet_wosib_script = "http://%s%s?store_url={{ shop.permanent_domain }}";
                var _willet_cart_items = [
                    {%% for item in cart.items %%}
                        { "id" : "{{ item.id }}",
                          "image" : "{{ item.image }}" || _willet_no_image, // url
                          "title" : "{{ item.title }}", // or "name"
                          "variant_id" : "{{ item.variant_id }}"
                        },
                    {%% endfor %%}
                ];

                var _willet_st = document.createElement( 'script' );
                _willet_st.type = 'text/javascript';
                _willet_st.src = _willet_wosib_script;
                $(document).prepend(_willet_st);
            </script>''' % (DOMAIN, DOMAIN, reverse_url('WOSIBShopifyServeScript'))

        liquid_assets = [{
            'asset': {
                'value': script_src,
                'key': 'snippets/willet_wosib.liquid'
            }
        }]
        # Install yourself in the Shopify store
        logging.debug ("installing WOSIB webhooks")
        self.install_webhooks()
        logging.debug ("installing WOSIB assets")
        self.install_assets(assets=liquid_assets)

    def put(self):
        """So we memcache by the store_url as well"""
        logging.info('enhanced WOSIBShopify put')
        super(WOSIBShopify, self).put()
        self.memcache_by_store_url()

    def memcache_by_store_url(self):
        return memcache.set(
                "WOSIB-%s" % self.store_url, # url collides with SIBT memcache
                db.model_to_protobuf(self).Encode(), time=MEMCACHE_TIMEOUT)

    @staticmethod
    def create(client, token):
        uuid = generate_uuid( 16 )
        app = WOSIBShopify (
                        key_name    = uuid,
                        uuid        = uuid,
                        client      = client,
                        store_name  = client.name, # Store name
                        store_url   = client.url, # Store url
                        store_id    = client.id, # Store id
                        store_token = token)
        logging.debug ("app %s ready to put" % app)
        app.put()
        
        app.do_install()
       
        return app

    @staticmethod
    def get_or_create(client, token=None):
        logging.debug ("in get_or_create, client.url = %s" % client.url)
        app = WOSIBShopify.get_by_store_url(client.url)
        if app is None:
            logging.debug ("app not found; creating one.")
            app = WOSIBShopify.create(client, token)
        elif token != None and token != '':
            logging.debug("WOSIB: Have both app and token")
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
                    logging.debug ("app.old_client was %s" % app.old_client)
                    app.client      = app.old_client
                    app.old_client  = None
                    app.put()

                    app.do_install()
                except:
                    logging.error('encountered error with reinstall', exc_info=True)
            else:
                logging.debug("WOSIB: token matches")
        else:
            # if token is None
            logging.debug("token is None")
            pass
        logging.debug ("WOSIBShopify::get_or_create.app is now %s" % app)
        return app

    @staticmethod
    def get_by_uuid(uuid):
        return WOSIBShopify.get(uuid)

    @staticmethod
    def get_by_store_url(url):
        data = memcache.get("WOSIB-%s" % url)
        if data:
            app = db.model_from_protobuf(entity_pb.EntityProto(data))
        else:
            app = WOSIBShopify.all()\
                .filter('store_url =', url)\
                .get()
            if app:
                app.memcache_by_store_url()
        if app is None:
            logging.warn ("store is Nothing, memcache and DB!")
        return app


