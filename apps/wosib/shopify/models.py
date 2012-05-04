#!/usr/bin/python

"""WOSIBShopify model extends WOSIB to provide Shopify-specific snippets."""

__author__ = "Willet, Inc."
__copyright__ = "Copyright 2012, Willet, Inc"

import logging
import urlparse

from google.appengine.api import memcache
from google.appengine.datastore import entity_pb
from google.appengine.ext import db

from apps.app.shopify.models import AppShopify
from apps.wosib.models import WOSIB
from util.consts import DOMAIN, MEMCACHE_TIMEOUT
from util.helpers import generate_uuid
from util.helpers import url as reverse_url
from util.shopify_helpers import get_url_variants

# -----------------------------------------------------------------------------
# WOSIBShopify Class Definition -----------------------------------------------
# -----------------------------------------------------------------------------
class WOSIBShopify(WOSIB, AppShopify):
    """WOSIBShopify objects are datastore-bound Apps (i.e. cannot be installed
    individually) that assist SIBT/SIBTShopify Apps in asking multi-product
    questions.

    The WOSIBShopify App communicates with Shopify using the SIBTShopify app.
    """

    def __init__(self, *args, **kwargs):
        """ Initialize this model """
        super(WOSIBShopify, self).__init__(*args, **kwargs)

    def _validate_self(self):
        return True

    def do_install(self, email_client=True):
        # "You must escape a percent sign with another percent sign." TIL.
        """Installs this instance"""
        script_src = """<!-- START willet WOSIB for Shopify -->
            <div id="_willet_WOSIB_Button" style="width:278px;height:88px;"></div>
            <script type="text/javascript">
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

                // remove trailing element... IE7 trailing comma patch
                _willet_cart_items.pop();

                (function (s) {
                    s.type = 'text/javascript';
                    s.src = _willet_wosib_script;
                    document.getElementsByTagName("head")[0].appendChild(s);
                }(document.createElement('script')));
            </script>""" % (DOMAIN, DOMAIN, reverse_url('SIBTServeScript'))

        liquid_assets = [{
            'asset': {
                'value': script_src,
                'key': 'snippets/willet_wosib.liquid'
            }
        }]
        # Install yourself in the Shopify store
        self.queue_webhooks(product_hooks_too=False)
        self.queue_assets(assets=liquid_assets)

        self.install_queued()

    def _memcache_by_store_url(self):
        """Memcache in addition to that of the Model class."""
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
        self._memcache_by_store_url()
        super(WOSIBShopify, self).put()

    @staticmethod
    def create(client, token, email_client=True):
        uuid = generate_uuid(16)
        app = WOSIBShopify(key_name=uuid,
                           uuid=uuid,
                           client=client,
                           store_name=client.name,  # Store name
                           store_url=client.url,  # Store url
                           store_id=client.id,  # Store id
                           store_token=token)
        app.put()

        app.do_install(email_client)

        return app

    @staticmethod
    def get_or_create(client, token=None, email_client=True):
        logging.debug ("in get_or_create, client.url = %s" % client.url)
        app = WOSIBShopify.get_by_store_url(client.url)
        if app is None:
            app = WOSIBShopify.create(client, token)
        elif token != None and token != '':
            if app.store_token != token:
                # TOKEN mis match, this might be a re-install
                logging.warn("Reinstalling app.")
                try:
                    app.store_token = token
                    app.old_client = app.client
                    if client:
                        app.client = client
                    app.put()

                    app.do_install(email_client)
                except Exception:
                    logging.error('Encountered error with reinstall',
                                  exc_info=True)
        return app

    @staticmethod
    def get_by_uuid(uuid):
        return WOSIBShopify.get(uuid)

    @staticmethod
    def get_by_store_url(url):
        www_url = url
        if not url:
            return None  # can't get by store_url if no URL given

        (url, www_url) = get_url_variants(url, keep_path=False)

        data = memcache.get("WOSIB-%s" % url)
        if data:
            return db.model_from_protobuf(entity_pb.EntityProto(data))

        data = memcache.get("WOSIB-%s" % www_url)
        if data:
            return db.model_from_protobuf(entity_pb.EntityProto(data))

        # "first get by url, then by www_url"
        app = WOSIBShopify.all().filter('store_url IN', [url, www_url]).get()
        if not app:
            # no app in DB by store_url; try again with extra_url
            app = WOSIBShopify.all().filter('extra_url IN', [url, www_url]).get()

        if app:
            app._memcache_by_store_url()
        return app
