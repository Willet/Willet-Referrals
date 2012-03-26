#!/usr/bin/python

# WOSIBShopify model

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2012, Willet, Inc"

import datetime
import hashlib
import inspect
import logging

from django.utils                import simplejson as json
from google.appengine.api        import memcache
from google.appengine.datastore  import entity_pb
from google.appengine.ext        import db
from google.appengine.ext.webapp import template

from apps.app.shopify.models     import AppShopify
from apps.client.models          import Client
from apps.email.models           import Email
from apps.user.models            import User
from apps.wosib.models           import WOSIB 
from util                        import httplib2
from util.consts                 import *
from util.helpers                import generate_uuid
from util.helpers                import url as reverse_url

# ------------------------------------------------------------------------------
# WOSIBShopify Class Definition -------------------------------------------------
# ------------------------------------------------------------------------------
class WOSIBShopify(WOSIB, AppShopify):
    
    # NOTE
    # WOSIB is a subset of SIBT, and, as such, does not have a version number.
    # To obtain the WOSIB version, load its SIBT counterpart 
    # with get_by_store_url() and read its version number.
    # version    = db.StringProperty(default='2', indexed=False)
    
    def __init__(self, *args, **kwargs):
        """ Initialize this model """
        super(WOSIBShopify, self).__init__(*args, **kwargs)
    
    def _validate_self(self):
        return True

    def do_install(self, email_client=True):
        # "You must escape a percent sign with another percent sign." TIL.
        """Installs this instance"""
        script_src = '''<!-- START willet wosib for Shopify -->
            <div id="_willet_WOSIB_Button" style="width:278px;height:88px;"></div>
            <script type="text/javascript">
                var _willet_no_image = "http://%s/static/imgs/noimage.png";
                var _willet_wosib_script = "http://%s%s?store_url={{ shop.permanent_domain }}";
                var _willet_cart_items = [
                    {%% for item in cart.items %%}
                        { "image" : "{{ item.image }}" || _willet_no_image, // url
                          "title" : "{{ item.title }}", // or "name"
                          "id" : "{{ item.product.id }}",
                          "product_url" : "{{ item.product.url }}"
                        },
                    {%% endfor %%}
                {}];
                _willet_cart_items.pop(); // remove trailing element... IE7 trailing comma patch

                var _willet_st = document.createElement( 'script' );
                _willet_st.type = 'text/javascript';
                _willet_st.src = _willet_wosib_script;
                window.document.getElementsByTagName("head")[0].appendChild(_willet_st);
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

    def _memcache_by_store_url(self):
        success1 = memcache.set(
                "WOSIB-%s" % self.store_url,
                db.model_to_protobuf(self).Encode(), time=MEMCACHE_TIMEOUT)
        if hasattr (self, 'extra_url'):
            # if you have an extra URL, you need to memcache the app by extra URL as well.
            success2 = memcache.set(
                    "WOSIB-%s" % self.extra_url,
                    db.model_to_protobuf(self).Encode(), time=MEMCACHE_TIMEOUT)
            return success1 and success2
        return success1

    def put(self):
        """So we memcache by the store_url as well"""
        logging.info('enhanced WOSIBShopify put')
        self._memcache_by_store_url()
        super(WOSIBShopify, self).put()

    @staticmethod
    def create(client, token, email_client=True):
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
        
        app.do_install(email_client)
       
        return app

    @staticmethod
    def get_or_create(client, token=None, email_client=True):
        logging.debug ("in get_or_create, client.url = %s" % client.url)
        app = WOSIBShopify.get_by_store_url(client.url)
        if app is None:
            logging.debug ("app not found; creating one.")
            app = WOSIBShopify.create(client, token)
        elif token != None and token != '':
            logging.debug("WOSIB: Have both app and token")
            if app.store_token != token:
                # TOKEN mis match, this might be a re-install
                logging.warn("client and app token mismatch; reinstalling app.")
                try:
                    app.store_token = token
                    app.old_client = app.client
                    if client:
                        app.client = client
                    app.put()

                    app.do_install(email_client)
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
            return db.model_from_protobuf(entity_pb.EntityProto(data))

        app = WOSIBShopify.all().filter('store_url =', url).get()
        if not app:
            # no app in DB by store_url; try again with extra_url
            app = WOSIBShopify.all().filter('extra_url =', url).get()
        
        if app:
            app._memcache_by_store_url()
        return app
