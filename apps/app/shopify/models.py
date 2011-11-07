#!/usr/bin/python

# The App Model
# A parent class for all social 'apps'
# ie. Referral, 'Should I buy this?', etc

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc"

import hashlib
#import logging, random, urllib2, datetime

from django.utils         import simplejson as json
#from google.appengine.api import memcache
#from google.appengine.api import urlfetch
#from google.appengine.api import taskqueue
from google.appengine.ext import db
#from google.appengine.ext.db import polymodel

from apps.app.models    import App
from apps.email.models  import Email

from util.consts        import *
from util               import httplib2
from util.model         import Model

NUM_SHARE_SHARDS = 15

class AppShopify(Model):
    # Shopify's ID for this store
    store_id  = db.StringProperty(indexed = True)
    
    store_url = db.StringProperty(indexed = True)

    # Shopify's token for this store
    store_token = db.StringProperty(indexed = True)

    def __init__(self, *args, **kwargs):
        super(AppShopify, self).__init__(*args, **kwargs)
        self.get_settings()
    
    def get_settings(self):
        class_name = self.class_name()
        self.settings = None 
        try:
            self.settings = SHOPIFY_APPS[class_name]
        except Exception, e:
            logging.error('could not get settings for app %s: %s' % (
                    class_name,
                    e
                )
            )

    # Shopify API Calls ------------------------------------------------------------
    def install_webhooks(self, webhooks=None):
        """ Install the webhooks into the Shopify store """
        # pass extra webhooks as a list
        if webhooks == None:
            webhooks = []

        logging.info("TOKEN %s" % self.store_token )

        url      = '%s/admin/webhooks.json' % self.store_url
        username = self.settings['api_key'] 
        password = hashlib.md5(self.settings['api_secret'] + self.store_token).hexdigest()
        header   = {'content-type':'application/json'}
        h        = httplib2.Http()
        
        # Auth the http lib
        h.add_credentials(username, password)
        
        # Install the "App Uninstall" webhook
        data = {
            "webhook": {
                "address": "%s/a/shopify/webhook/uninstalled/%s/" % (
                    URL,
                    self.class_name()
                ),
                "format": "json",
                "topic": "app/uninstalled"
            }
        }
        webhooks.append(data)
        
        # Install the "Order Creation" webhook
        data = {
            "webhook": {
                "address": "%s/o/shopify/webhook/create" % ( URL ),
                "format" : "json",
                "topic"  : "orders/create"
            }
        }
        webhooks.append(data)

        # Install the "Product Creation" webhook
        data = {
            "webhook": {
                "address": "%s/product/shopify/webhook/create" % ( URL ),
                "format" : "json",
                "topic"  : "products/create"
            }
        }
        webhooks.append(data)
        
        # Install the "Product Update" webhook
        data = {
            "webhook": {
                "address": "%s/product/shopify/webhook/update" % ( URL ),
                "format" : "json",
                "topic"  : "products/update"
            }
        }
        webhooks.append(data)

        for webhook in webhooks:
            logging.info('Installing extra hook %s' % webhook)
            logging.info("POSTING to %s %r " % (url, webhook))
            resp, content = h.request(
                url,
                "POST",
                body = json.dumps(webhook),
                headers = header
            )
            logging.info('%r %r' % (resp, content)) 
            if int(resp.status) == 401:
                Email.emailBarbara(
                    '%s WEBHOOK INSTALL FAILED\n%s\n%s' % (
                        self.class_name(),
                        resp,
                        content
                    )        
                )
        logging.info('installed %d webhooks' % len(webhooks))
        
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
        
        # Install the 'Order Confirmation Screen' script
        data = {
            "script_tag": {
                "src": "%s/o/shopify/order.js?store=%s" % (
                    SECURE_URL,
                    self.store_url 
                ),
                "event": "onload"
            }
        }      
        script_tags.append(data)
        
        for script_tag in script_tags:
            logging.info("POSTING to %s %r " % (url, script_tag) )
            resp, content = h.request(
                url,
                "POST",
                body = json.dumps(script_tag),
                headers = header
            )
            logging.info('%r %r' % (resp, content))
            if int(resp.status) == 401:
                Email.emailBarbara(
                    '%s SCRIPT_TAGS INSTALL FAILED\n%s\n%s' % (
                        self.class_name(),
                        resp,
                        content
                    )        
                )
        logging.info('installed %d script_tags' % len(script_tags))

    def install_assets(self, assets=None):
        """Installs our assets on the clients store
            Must first get the `main` template in use"""
        username = self.settings['api_key'] 
        password = hashlib.md5(self.settings['api_secret'] + self.store_token).hexdigest()
        header   = {'content-type':'application/json'}
        h        = httplib2.Http()
        h.add_credentials(username, password)
        
        main_id = None

        if assets == None:
            assets = []

        # get the theme ID
        theme_url = '%s/admin/themes.json' % self.store_url
        logging.info('Getting themes %s' % theme_url)
        resp, content = h.request(theme_url, 'GET', headers = header)

        if int(resp.status) == 200:
            # we are okay
            content = json.loads(content)
            for theme in content['themes']:
                if theme.role == 'main':
                    main_id = theme.id
                    break
        else:
            logging.error('%s error getting themes: \n%s\n%s' % (
                self.class_name(),
                resp,
                content
            ))
            return

        # now post all the assets
        url = '%s/admin/themes/%d/assets.json' % (self.store_url, main_id)
        for asset in assets: 
            logging.info("POSTING to %s %r " % (url, asset) )
            resp, content = h.request(
                url,
                "PUT",
                body = json.dumps(asset),
                headers = header
            )
            logging.info('%r %r' % (resp, content))
            if int(resp.status) != 200: 
                Email.emailBarbara(
                    '%s SCRIPT_TAGS INSTALL FAILED\n%s\n%s' % (
                        self.class_name(),
                        resp,
                        content
                    )        
                )

        logging.info('installed %d assets' % len(assets))

