#!/usr/bin/python

# The App Model
# A parent class for all social 'apps'
# ie. Referral, 'Should I buy this?', etc

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc"

import hashlib, logging, random, urllib2, datetime

from decimal              import *
from django.utils         import simplejson as json
from google.appengine.api import memcache
from google.appengine.api import urlfetch
from google.appengine.api import taskqueue
from google.appengine.ext import db
from google.appengine.ext.db import polymodel

from apps.link.models     import Link, get_link_by_willt_code 
from apps.user.models     import User

from util.consts          import *
from util.helpers         import generate_uuid
from util.helpers         import url 
from util.model           import Model
from util.memcache_ref_prop import MemcacheReferenceProperty

NUM_SHARE_SHARDS = 15

class App(Model, polymodel.PolyModel):
    # static memcache class name
    memcache_class = 'app'

    # Unique identifier for memcache and DB key
    uuid            = db.StringProperty( indexed = True )
    
    # Datetime when this model was put into the DB
    created         = db.DateTimeProperty( auto_now_add=True )
    
    # Person who created/installed this App
    client          = db.ReferenceProperty( db.Model, collection_name = 'apps' )
    
    # Defaults to None, only set if this App has been deleted
    old_client      = db.ReferenceProperty( db.Model, collection_name = 'deleted_apps' )
    
    # Analytics for this App
    analytics       = db.ReferenceProperty( db.Model, collection_name = "APPS" )
    
    # For Apps that use a click counter, this is the cached amount
    cached_clicks_count = db.IntegerProperty( default = 0 )
    
    def __init__(self, *args, **kwargs):
        self._memcache_key = kwargs['uuid'] if 'uuid' in kwargs else None 
        super(App, self).__init__(*args, **kwargs)
    
    @staticmethod
    def _get_from_datastore(uuid):
        """Datastore retrieval using memcache_key"""
        return App.all().filter('uuid =', uuid).get()

    def validateSelf( self ):
        # Subclasses should override this
        return

    def handleLinkClick( self ):
        # Subclasses must override this
        logging.error("THIS FCN SHOULD NEVER GET CALLED. FIX ME.")
        raise Exception("THIS FCN SHOULD NEVER GET CALLED. SUBCLASS ME!")

    def delete( self ):
        self.old_client = self.client
        self.client     = None
        self.put()
    
    @staticmethod
    def get_by_client( client ):
        return App.all().filter( 'client =', client )

    def count_clicks( self ):
        # Get an updated value by putting this on a queue
        taskqueue.add(
            queue_name = 'app-ClicksCounter', 
            url = '/a/appClicksCounter', 
            name = 'app_ClicksCounter_%s_%s' % (
                self.uuid,
                generate_uuid( 10 )),
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

def get_app_by_id( id ):
    logging.warn("Use App.get() !!!")
    #return App.all().filter( 'uuid =', id ).get()
    return App.get(id)

## -----------------------------------------------------------------------------
## -----------------------------------------------------------------------------
## -----------------------------------------------------------------------------
class ShareCounter(db.Model):
    """Sharded counter for link click-throughs"""

    app_id = db.StringProperty(indexed=True, required=True)
    count  = db.IntegerProperty(indexed=False, required=True, default=0)

## -----------------------------------------------------------------------------
## -----------------------------------------------------------------------------
## -----------------------------------------------------------------------------
class Conversion(Model):
    """Model storing conversion data"""
    uuid     = db.StringProperty( indexed = True )
    created  = db.DateTimeProperty(auto_now_add=True)
    link     = db.ReferenceProperty( db.Model, collection_name="link_conversions" )
    referrer = MemcacheReferenceProperty( db.Model, collection_name="users_referrals" )
    referree = MemcacheReferenceProperty( db.Model, default = None, collection_name="users_been_referred" )
    referree_uid = db.StringProperty()
    app      = db.ReferenceProperty( db.Model, collection_name="app_conversions" )
    order    = db.StringProperty()

    def __init__(self, *args, **kwargs):
        self._memcache_key = kwargs['uuid'] if 'uuid' in kwargs else None 
        super(Conversion, self).__init__(*args, **kwargs)
    
    @staticmethod
    def _get_from_dataapp( uuid ):
        """Dataapp retrieval using memcache_key"""
        return db.Query(Conversion).filter('uuid =', uuid).get()

def create_conversion( link, app, referree_uid, referree, order_num ):
    uuid = generate_uuid(16)
    
    c = Conversion( key_name     = uuid,
                    uuid         = uuid,
                    link         = link,
                    referrer     = link.user,
                    referree     = referree,
                    referree_uid = referree_uid,
                    app          = app,
                    order        = order_num )
    c.put()

    return c # return incase the caller wants it
