#!/usr/bin/python

# The App Model
# A parent class for all social 'apps'
# ie. Referral, 'Should I buy this?', etc

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc"

import hashlib
import re

from django.utils import simplejson as json
from google.appengine.ext import db

from apps.app.models import App
from apps.email.models import Email

from util import httplib2
from util.consts import *
from util.shopify_helpers import *
from util.model import Model

NUM_SHARE_SHARDS = 15


class AppShopify(App):
    """ Model for storing information about a Shopify App.
        AppShopify classes need not be installable from the Shopify app store,
        and can be installed as a bundle. Refer to SIBTShopify for example code.
    """
    store_id  = db.StringProperty(indexed = True) # Shopify's ID for this store
    store_token = db.StringProperty(indexed = True) # Shopify token for this store

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
    def install_webhooks(self, product_hooks_too=True, webhooks=None):
        """ Install the webhooks into the Shopify store """
        # pass extra webhooks as a list
        if webhooks == None:
            webhooks = []

        url      = '%s/admin/webhooks.json' % self.store_url
        username = self.settings['api_key'] 
        password = hashlib.md5(self.settings['api_secret'] + self.store_token).hexdigest()
        header   = {'content-type':'application/json'}
        h        = httplib2.Http()
        
        # Auth the http lib
        h.add_credentials(username, password)
        
        # See what we've already installed and flag it so we don't double install
        if product_hooks_too:
            # First fetch webhooks that already exist
            resp, content = h.request( url, "GET", headers = header)
            data = json.loads(content) 
            #logging.info('%s %s' % (resp, content))

            product_create = product_delete = product_update = True
            for w in data['webhooks']:
                if w['address'] == '%s/product/shopify/webhook/create' % URL or \
                   w['address'] == '%s/product/shopify/webhook/create/' % URL:
                    product_create = False
                if w['address'] == '%s/product/shopify/webhook/delete' % URL or \
                   w['address'] == '%s/product/shopify/webhook/delete/' % URL:
                    product_delete = False
                if w['address'] == '%s/product/shopify/webhook/update' % URL or \
                   w['address'] == '%s/product/shopify/webhook/update/' % URL:
                    product_update = False
        
        # If we don't want to install the product webhooks, 
        # flag all as "already installed"
        else:
            product_create = product_delete = product_update = False

        # Install the "App Uninstall" webhook
        webhooks.append({
            "webhook": {
                "address": "%s/a/shopify/webhook/uninstalled/%s/" % (
                    URL,
                    self.class_name()
                ),
                "format": "json",
                "topic": "app/uninstalled"
            }
        })

        # Install the "Product Creation" webhook
        if product_create:
            webhooks.append({
                "webhook": {
                    "address": "%s/product/shopify/webhook/create" % ( URL ),
                    "format" : "json",
                    "topic"  : "products/create"
                }
            })
        
        # Install the "Product Update" webhook
        if product_update:
            webhooks.append({
                "webhook": {
                    "address": "%s/product/shopify/webhook/update" % ( URL ),
                    "format" : "json",
                    "topic"  : "products/update"
                }
            })

        # Install the "Product Delete" webhook
        if product_delete:
            webhooks.append({
                "webhook": {
                    "address": "%s/product/shopify/webhook/delete" % ( URL ),
                    "format" : "json",
                    "topic"  : "products/delete"
                }
            })

        for webhook in webhooks:
            resp, content = h.request(
                url,
                "POST",
                body = json.dumps(webhook),
                headers = header
            )
            
            if 200 <= int(resp.status) <= 299:
                # HTTP status 200's == success
                logging.info('Installed webhook, %s: %s' % (resp.status, webhook['webhook']['topic']))
            else:
                error_msg = 'Webhook install failed, %s: %s\n%s\n%s\n%s' % (
                        resp.status,
                        webhook['webhook']['topic'],
                        self.store_url,
                        resp,
                        content
                    )
                logging.error(error_msg)
                Email.emailDevTeam(error_msg)
        
    def install_script_tags(self, script_tags=None):
        """ Install our script tags onto the Shopify store """
        if script_tags == None:
            script_tags = []

        url      = '%s/admin/script_tags.json' % self.store_url
        username = self.settings['api_key'] 
        password = hashlib.md5(self.settings['api_secret'] + self.store_token).hexdigest()
        header   = {'content-type':'application/json'}
        h        = httplib2.Http()
        
        h.add_credentials(username, password)
        
        for script_tag in script_tags:
            resp, content = h.request(
                url,
                "POST",
                body = json.dumps(script_tag),
                headers = header
            )

            if 200 <= int(resp.status) <= 299:
                # HTTP status 200's == success
                logging.info('Installed script tag, %s: %s' % (resp.status, script_tag['script_tag']['src']))
            else:
                error_msg = 'Script tag install failed, %s: %s\n%s\n%s\n%s' % (
                    resp.status,
                    script_tag['script_tag']['src'],
                    self.store_url,
                    resp,
                    content
                )
                logging.error(error_msg)
                Email.emailDevTeam(error_msg)

    def install_assets(self, assets=None):
        """Installs our assets on the client's store
            Must first get the `main` template in use"""
        if not assets:
            logging.warn('No assets to install')
            return
        
        username = self.settings['api_key'] 
        password = hashlib.md5(self.settings['api_secret'] + self.store_token).hexdigest()
        header   = {'content-type':'application/json'}
        h        = httplib2.Http()
        h.add_credentials(username, password)
        
        main_id = None

        # get the theme ID
        theme_url = '%s/admin/themes.json' % self.store_url
        resp, content = h.request(theme_url, 'GET', headers = header)

        if 200 <= int(resp.status) <= 299:
            # HTTP status 200's == success
            content = json.loads(content)
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

        # now post all the assets
        url = '%s/admin/themes/%d/assets.json' % (self.store_url, main_id)
        for asset in assets: 
            resp, content = h.request(
                url,
                "PUT",
                body = json.dumps(asset),
                headers = header
            )
            
            if 200 <= int(resp.status) <= 299:
                # HTTP status 200's == success
                logging.info('Installed asset, %s: %s' % (resp.status, asset['asset']['key']))
            else:
                error_msg = 'Script tag install failed, %s: %s\n%s\n%s\n%s' % (
                    resp.status,
                    asset['asset']['key'],
                    self.store_url,
                    resp,
                    content
                )
                logging.error(error_msg)
                Email.emailDevTeam(error_msg)
# end class
