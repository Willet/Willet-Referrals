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
    ''' Model for storing information about a Shopify App.
        AppShopify classes need not be installable from the Shopify app store,
        and can be installed as a bundle. Refer to SIBTShopify for example code.
    '''
    
    # Shopify's ID for this store
    store_id  = db.StringProperty(indexed = True)
    
    # must be the .shopify.com (e.g. http://thegoodhousewife.myshopify.com)
    store_url = db.StringProperty(indexed = True)
    
    # other domains (e.g. http://thegoodhousewife.co.nz)
    extra_url = db.StringProperty(indexed = True, required = False, default = '')

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
    def install_webhooks(self, product_hooks_too=True, webhooks=None):
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
        
        # See what we've already installed and flag it so we don't double install
        if product_hooks_too:
            # First fetch webhooks that already exist
            resp, content = h.request( url, "GET", headers = header)
            data = json.loads( content ) 
            #logging.info('%s %s' % (resp, content))

            product_create = product_delete = product_update = True
            for w in data['webhooks']:
                #logging.info("checking %s"% w['address'])
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

        # Install the "Product Creation" webhook
        data = {
            "webhook": {
                "address": "%s/product/shopify/webhook/create" % ( URL ),
                "format" : "json",
                "topic"  : "products/create"
            }
        }
        if product_create:
            webhooks.append(data)
        
        # Install the "Product Update" webhook
        data = {
            "webhook": {
                "address": "%s/product/shopify/webhook/update" % ( URL ),
                "format" : "json",
                "topic"  : "products/update"
            }
        }
        if product_update:
            webhooks.append(data)

        # Install the "Product Delete" webhook
        data = {
            "webhook": {
                "address": "%s/product/shopify/webhook/delete" % ( URL ),
                "format" : "json",
                "topic"  : "products/delete"
            }
        }
        if product_delete:
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
                Email.emailDevTeam(
                    '%s WEBHOOK INSTALL FAILED\n%s\n%s\n%s' % (
                        self.class_name(),
                        resp,
                        self.store_url,
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
                Email.emailDevTeam(
                    '%s SCRIPT_TAGS INSTALL FAILED\n%s\n%s' % (
                        self.class_name(),
                        resp,
                        content
                    )        
                )
        logging.info('installed %d script_tags' % len(script_tags))

    def install_assets(self, assets=None):
        """Installs our assets on the client's store
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
                if 'role' in theme and 'id' in theme:
                    if theme['role'] == 'main':
                        main_id = theme['id']
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
                Email.emailDevTeam(
                    '%s SCRIPT_TAGS INSTALL FAILED\n%s\n%s' % (
                        self.class_name(),
                        resp,
                        content
                    )        
                )

        logging.info('installed %d assets' % len(assets))

