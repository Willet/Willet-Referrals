#!/usr/bin/python

"""The App Model.

A parent class for all social 'apps'
ie. Referral, 'Should I buy this?', etc
"""

__author__ = "Willet, Inc."
__copyright__ = "Copyright 2012, Willet, Inc"

import logging
import random

from decimal import *
from google.appengine.api import memcache
from google.appengine.api import taskqueue
from google.appengine.ext import db
from google.appengine.ext.db import polymodel

from util.consts import *
from util.helpers import generate_uuid
from util.model import Model
from util.memcache_ref_prop import MemcacheReferenceProperty
from util.shopify_helpers import get_url_variants

NUM_SHARE_SHARDS = 15


class App(Model, polymodel.PolyModel):
    """Model for storing any app."""
    # static memcache class name
    memcache_class = 'app'

    # For Apps that use a click counter, this is the cached amount
    cached_clicks_count = db.IntegerProperty(default=0)

    # Person who created/installed this App
    client = db.ReferenceProperty(db.Model, collection_name='apps')

    # Datetime when this model was put into the DB
    created = db.DateTimeProperty(auto_now_add=True)
    # Defaults to None, only set if this App has been deleted
    old_client = db.ReferenceProperty(db.Model, collection_name='deleted_apps')

    # must be the http://*.myshopify.com if AppShopify
    store_url = db.StringProperty(indexed=True)
    # custom domain
    extra_url = db.StringProperty(indexed=True, required=False, default='')

    # Version number of the app
    # Version 1 = [Beginning, Nov. 22, 2011]
    # Version 2 = [Nov. 23, 2011, Feb. 2012]
    # version 3: "sweet buttons upgrade"
    # version 10: SIBT-JS, SIBT2 (add WOSIB-like functionality)
    # version 11: ReEngage
    version = db.StringProperty(default='11', indexed=False)
    # STRING property of any integer
    # change on upgrade; new installs get this as version.
    CURRENT_INSTALL_VERSION = '11'

    def __init__(self, *args, **kwargs):
        self._memcache_key = kwargs['uuid'] if 'uuid' in kwargs else None
        super(App, self).__init__(*args, **kwargs)

    def _validate_self(self):
        return True

    def delete(self):
        """ When someone uninstalls, put in a saved state """
        self.old_client = self.client
        self.client = None
        self.put()

    # Stubs -------------------------------------------------------------------
    # TODO: rename function in under_score_name
    def handleLinkClick(self):
        """ Called when a link associated with the app is clicked """
        # Subclasses must override this
        err_msg = 'handleLinkClick should be implemented by <%s.%s>'
        raise NotImplementedError(err_msg % (self.__class__.__module__,
                                             self.__class__.__name__))

    # Accessors ---------------------------------------------------------------
    @classmethod
    def get_by_client(cls, client):
        return cls.all().filter('client =', client).get()

    @classmethod
    def get_by_url(cls, store_url):
        """Fetch an app via the store's url. This app can be of any type,
        and of any subclass. Use subclass-specific get_by_url functions
        to obtain more precise targets.
        """
        urls = get_url_variants(store_url, keep_path=False)

        logging.info("Looking for App in %r" % urls)
        app = cls.all().filter('store_url IN', urls).get()
        if app:
            return app

        app = cls.all().filter('extra_url IN', urls).get()
        return app

    # Counters ----------------------------------------------------------------
    def count_clicks(self):
        # Get an updated value by putting this on a queue
        taskqueue.add(
            queue_name = 'app-ClicksCounter',
            url = '/a/appClicksCounter',
            name = 'app_ClicksCounter_%s_%s' % (
                self.uuid,
                generate_uuid(10)),
            params = {
                'app_uuid' : self.uuid
            }
        )
        # Return an old cached value
        return self.cached_clicks_count

    def get_shares_count(self):
        """Count this apps sharded shares"""
        total = memcache.get(self.uuid+"ShareCounter")
        if total is None:
            total = 0
            for counter in ShareCounter.all().\
            filter('app_id =', self.uuid).fetch(15):
                total += counter.count
            memcache.add(key=self.uuid+"ShareCounter", value=total)
        return total

    def add_shares(self, num):
        """add num clicks to this app's share counter"""
        def txn():
            index = random.randint(0, NUM_SHARE_SHARDS-1)
            shard_name = self.uuid + str(index)
            counter = ShareCounter.get_by_key_name(shard_name)
            if counter is None:
                counter = ShareCounter(key_name=shard_name,
                                       app_id=self.uuid)
            counter.count += num
            counter.put()

        db.run_in_transaction(txn)
        memcache.incr(self.uuid+"ShareCounter")

    def increment_shares(self):
        """Increment this link's click counter"""
        self.add_shares(1)


class ShareCounter(db.Model):
    """Sharded counter for link click-throughs"""
    app_id = db.StringProperty(indexed=True, required=True)
    count = db.IntegerProperty(indexed=False, required=True, default=0)

