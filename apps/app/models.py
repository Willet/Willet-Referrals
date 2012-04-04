#!/usr/bin/python

# The App Model
# A parent class for all social 'apps'
# ie. Referral, 'Should I buy this?', etc

__author__ = "Willet, Inc."
__copyright__ = "Copyright 2011, Willet, Inc"

import hashlib, logging, random, urllib2, datetime

from decimal import *
from django.utils import simplejson as json
from google.appengine.api import memcache
from google.appengine.api import urlfetch
from google.appengine.api import taskqueue
from google.appengine.ext import db
from google.appengine.ext.db import polymodel

from apps.link.models import Link
from apps.user.models import User

from util.consts import *
from util.helpers import generate_uuid
from util.helpers import url 
from util.model import Model
from util.memcache_ref_prop import MemcacheReferenceProperty

NUM_SHARE_SHARDS = 15


class App(Model, polymodel.PolyModel):
    # static memcache class name
    memcache_class = 'app'
    
    # Datetime when this model was put into the DB
    created = db.DateTimeProperty(auto_now_add=True)
    
    # Person who created/installed this App
    client = db.ReferenceProperty(db.Model, collection_name = 'apps')
    
    # Defaults to None, only set if this App has been deleted
    old_client = db.ReferenceProperty(db.Model, collection_name = 'deleted_apps')
    
    store_url = db.StringProperty(indexed = True) # must be the http://*.myshopify.com if AppShopify
    extra_url = db.StringProperty(indexed = True, required = False, default = '') # custom domain

    # For Apps that use a click counter, this is the cached amount
    cached_clicks_count = db.IntegerProperty(default = 0)

    # Version number of the app
    # Version 1 = [Beginning, Nov. 22, 2011]
    # Version 2 = [Nov. 23, 2011, Present]
    # Differences between versions: version 1 uses script_tags API to install scripts
    # version 2 uses asset api to include liquid
    # version 3: "sweet buttons upgrade"
    # version 10: merge SIBT into ShopConnection app
    version = db.StringProperty(default='10', indexed=False)
    
    # STRING property of any integer
    # change on upgrade; new installs get this as version.
    CURRENT_INSTALL_VERSION = '10'
    
    def __init__(self, *args, **kwargs):
        self._memcache_key = kwargs['uuid'] if 'uuid' in kwargs else None 
        super(App, self).__init__(*args, **kwargs)
    
    def _validate_self(self):
        return True

    @classmethod
    def _get_from_datastore(cls, uuid):
        """Datastore retrieval using memcache_key"""
        return cls.all().filter('uuid =', uuid).get()

    def delete(self):
        """ When someone uninstalls, put in a saved state """
        self.old_client = self.client
        self.client = None
        self.put()

    # Stubs --------------------------------------------------------------------
    # TODO: rename function in under_score_name
    def handleLinkClick(self):
        """ Called when a link associated with the app is clicked """ 
        # Subclasses must override this
        raise NotImplementedError('handleLinkClick should be implemented by <%s.%s>' % (self.__class__.__module__,
                                                                                        self.__class__.__name__))
    
    # Accessors --------------------------------------------------------------------
    @classmethod
    def get_by_client(cls, client):
        return cls.all().filter('client =', client).get()

    # Counters --------------------------------------------------------------------
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


def get_app_by_id(id):
    raise DeprecationWarning('Replaced by App.get_by_uuid')
    return App.get_by_uuid(id)

## -----------------------------------------------------------------------------
## -----------------------------------------------------------------------------
## -----------------------------------------------------------------------------
class ShareCounter(db.Model):
    """Sharded counter for link click-throughs"""

    app_id = db.StringProperty(indexed=True, required=True)
    count = db.IntegerProperty(indexed=False, required=True, default=0)

