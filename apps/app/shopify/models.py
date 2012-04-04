#!/usr/bin/python

# The App Model
# A parent class for all social 'apps'
# ie. Referral, 'Should I buy this?', etc

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc"

import base64
import hashlib
import re

from django.utils             import simplejson as json
from google.appengine.api     import urlfetch
from google.appengine.ext     import db
from google.appengine.runtime import DeadlineExceededError

from apps.app.models          import App
from apps.email.models        import Email

from util                     import httplib2
from util.consts              import *
from util.shopify_helpers     import *
from util.model               import Model

NUM_SHARE_SHARDS = 15


class AppShopify(Model):
    """ Model for storing information about a Shopify App.
        AppShopify classes need not be installable from the Shopify app store,
        and can be installed as a bundle. Refer to SIBTShopify for example code.
    """
    store_id  = db.StringProperty(indexed=True) # Shopify's ID for this store
    store_url = db.StringProperty(indexed=True) # must be the http://*.myshopify.com
    extra_url = db.StringProperty(indexed=True, required=False, default='') # custom domain
    store_token = db.StringProperty(indexed=True) # Shopify token for this store

    def __init__(self, *args, **kwargs):
        super(AppShopify, self).__init__(*args, **kwargs)
        self.get_settings()

    def _validate_self(self):
        if not re.match("(http|https)://[\w\-~]+.myshopify.com", self.store_url):
            raise ValueError("<%s.%s> has malformated store url '%s'" % (self.__class__.__module__, self.__class__.__name__, self.store_url))
        return True

    def get_settings(self):
        class_name = self.class_name()
        self.settings = None 
        try:
            self.settings = SHOPIFY_APPS[class_name]
        except Exception, e:
            logging.error('could not get settings for app %s: %s' % (class_name, e))

    # Retreivers ------------------------------------------------------------
    @classmethod
    def get_by_url(cls, store_url):
        """ Fetch a Shopify app via the store's url"""
        store_url = get_shopify_url(store_url)

        logging.info("Shopify: Looking for %s" % store_url)
        return cls.all().filter('store_url =', store_url).get()

    # Shopify API Calls ------------------------------------------------------------
    def queue_webhooks(self, product_hooks_too=False, webhooks=None):
        """ Determine which webhooks will have to be installed,
            and add them to the queue for parallel processing """
        # Avoids mutable default parameter [] error
        if not webhooks:
            webhooks = []

        url      = '%s/admin/webhooks.json' % self.store_url
        username = self.settings['api_key'] 
        password = hashlib.md5(self.settings['api_secret'] + self.store_token).hexdigest()
        headers  = {
            'content-type':'application/json',
            "Authorization": "Basic %s" % base64.b64encode(("%s:%s") % (username,password))
        }

        default_webhooks = [
            # Install the "App Uninstall" webhook
            { "webhook": { "address": "%s/a/shopify/webhook/uninstalled/%s/" % (URL, self.class_name()),
                           "format": "json", "topic": "app/uninstalled" }
            }
        ]

        if product_hooks_too:
            default_webhooks.extend([
                # Install the "Product Creation" webhook
                { "webhook": { "address": "%s/product/shopify/webhook/create" % ( URL ),
                               "format": "json", "topic": "products/create" }
                },
                # Install the "Product Update" webhook
                { "webhook": { "address": "%s/product/shopify/webhook/update" % ( URL ),
                               "format": "json", "topic": "products/update" }
                },
                # Install the "Product Delete" webhook
                { "webhook": { "address": "%s/product/shopify/webhook/delete" % ( URL ),
                               "format": "json", "topic": "products/delete" }
                }
            ])
        
            # See what we've already installed
            # First fetch webhooks that already exist
            data = None
            result = urlfetch.fetch(url=url, method='GET', headers=headers)
            
            if 200 <= int(result.status_code) <= 299:
                data = json.loads(result.content)
            else:
                error_msg = 'Error getting webhooks, %s: %s\n%s\n%s\n%s' % (
                    result.status_code,
                    url,
                    self.store_url,
                    result,
                    result.content
                )
                logging.error(error_msg)
                Email.emailDevTeam(error_msg)
                return
            
            # Dequeue whats already installed so we don't reinstall it
            for w in data['webhooks']:
                # Remove trailing '/'
                address = w['address'] if w['address'][-1:] != '/' else w['address'][:-1]
                
                for i, webhook in enumerate(default_webhooks):
                    if webhook['webhook']['address'] == address:
                        del(default_webhooks[i])
                        break
        
        webhooks.extend(default_webhooks)
        
        if webhooks:
            self._webhooks_url = url
            self._queued_webhooks = webhooks

    def queue_script_tags(self, script_tags=None):
        """ Determine which script tags will have to be installed,
            and add them to the queue for parallel processing """
        if not script_tags:
            return

        self._script_tags_url = '%s/admin/script_tags.json' % self.store_url
        self._queued_script_tags = script_tags

    def queue_assets(self, assets=None):
        """ Determine which assets will have to be installed,
            and add them to the queue for parallel processing """
        if not assets:
            return
        
        username = self.settings['api_key'] 
        password = hashlib.md5(self.settings['api_secret'] + self.store_token).hexdigest()
        headers = {
            'content-type':'application/json',
            "Authorization": "Basic %s" % base64.b64encode(("%s:%s") % (username,password))
        }
        theme_url = '%s/admin/themes.json' % self.store_url
        main_id = None

        # Find out which theme is in use
        result = urlfetch.fetch(url=theme_url, method='GET', headers=headers)

        if 200 <= int(result.status_code) <= 299:
            # HTTP status 200's == success
            content = json.loads(result.content)
            for theme in content['themes']:
                if 'role' in theme and 'id' in theme:
                    if theme['role'] == 'main':
                        main_id = theme['id']
                        break
        else:
            error_msg = 'Error getting themes, %s: %s\n%s\n%s\n%s' % (
                resp.status,
                theme_url,
                self.store_url,
                resp,
                content
            )
            logging.error(error_msg)
            Email.emailDevTeam(error_msg)

        self._assets_url = '%s/admin/themes/%d/assets.json' % (self.store_url, main_id)
        self._queued_assets = assets

    def install_queued(self):
        """ Install webhooks, script_tags, and assets in parallel 
            Note: first queue everything up, then call this!
        """
        # Callback function for webhooks
        def handle_webhook_result(rpc, webhook):
            resp = rpc.get_result()
            
            if 200 <= int(resp.status_code) <= 299:
                # HTTP status 200's == success
                logging.info('Installed webhook, %s: %s' % (resp.status_code, webhook['webhook']['topic']))
            else:
                error_msg = 'Webhook install failed, %s: %s\n%s\n%s\n%s' % (
                        resp.status_code,
                        webhook['webhook']['topic'],
                        self.store_url,
                        resp.headers,
                        resp.content
                    )
                logging.error(error_msg)
                Email.emailDevTeam(error_msg)

        # Callback function for script tags
        def handle_script_tag_result(rpc, script_tag):
            resp = rpc.get_result()

            if 200 <= int(resp.status_code) <= 299:
                # HTTP status 200's == success
                logging.info('Installed script tag, %s: %s' % (resp.status_code, script_tag['script_tag']['src']))
            else:
                error_msg = 'Script tag install failed, %s: %s\n%s\n%s\n%s' % (
                    resp.status_code,
                    script_tag['script_tag']['src'],
                    self.store_url,
                    resp,
                    content
                )
                logging.error(error_msg)
                Email.emailDevTeam(error_msg)

        # Callback function for assets
        def handle_asset_result(rpc, asset):
            resp = rpc.get_result()
            
            if 200 <= int(resp.status_code) <= 299:
                # HTTP status 200's == success
                logging.info('Installed asset, %s: %s' % (resp.status_code, asset['asset']['key']))
            else:
                error_msg = 'Script tag install failed, %s: %s\n%s\n%s\n%s' % (
                    resp.status_code,
                    asset['asset']['key'],
                    self.store_url,
                    resp,
                    content
                )
                logging.error(error_msg)
                Email.emailDevTeam(error_msg)

        # Use a helper function to define the scope of the callback
        def create_callback(callback_func, **kwargs):
            # Lambda function
            def deadline_exceeded_catch():
                try:
                    callback_func(**kwargs)
                except DeadlineExceededError:
                    params_str = '\n'.join([ "%s= %r" % (key, value) for key, value in kwargs.items()])
                    error_msg = 'Installation failed, deadline exceeded:\n%s' % (params_str,)
                    logging.error(error_msg)
                    Email.emailDevTeam(error_msg)

            return lambda: deadline_exceeded_catch()

        rpcs = []
        username = self.settings['api_key'] 
        password = hashlib.md5(self.settings['api_secret'] + self.store_token).hexdigest()
        headers = {
            'content-type':'application/json',
            "Authorization": "Basic %s" % base64.b64encode(("%s:%s") % (username,password))
        }

        # Fire off all queued requests
        if hasattr(self, '_queued_webhooks') and hasattr(self, '_webhooks_url'):
            for webhook in self._queued_webhooks:
                rpc = urlfetch.create_rpc()
                rpc.callback = create_callback(handle_webhook_result, rpc=rpc, webhook=webhook)
                urlfetch.make_fetch_call(rpc=rpc, url=self._webhooks_url, payload=json.dumps(webhook),
                                         method='POST', headers=headers)
                rpcs.append(rpc)

        if hasattr(self, '_queued_script_tags') and hasattr(self, '_script_tags_url'):
            for script_tag in self._queued_script_tags:
                rpc = urlfetch.create_rpc()
                rpc.callback = create_callback(handle_script_tag_result, rpc=rpc, script_tag=script_tag)
                urlfetch.make_fetch_call(rpc=rpc, url=self._script_tags_url, payload=json.dumps(script_tag),
                                         method='POST', headers=headers)
            rpcs.append(rpc)

        if hasattr(self, '_queued_assets') and hasattr(self, '_assets_url'):
            for asset in self._queued_assets:
                rpc = urlfetch.create_rpc()
                rpc.callback = create_callback(handle_asset_result, rpc=rpc, asset=asset)
                urlfetch.make_fetch_call(rpc=rpc, url=self._assets_url, payload=json.dumps(asset),
                                         method='POST', headers=headers)

        # Finish all RPCs, and let callbacks process the results.
        for rpc in rpcs:
            try:
                rpc.wait()
            except DeadlineExceededError:
                rpc.callback()
        
        # All callbacks finished
        return
# end class