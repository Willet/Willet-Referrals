#!/usr/bin/python

# WOSIB model
# Extends from "App"

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc"

import hashlib
import logging
import random
from datetime import datetime
from datetime import timedelta

from django.utils         import simplejson as json
from google.appengine.ext import db
from google.appengine.api import memcache
from google.appengine.datastore import entity_pb

from apps.app.models      import App
from apps.email.models    import Email
from apps.link.models     import Link
from apps.user.models     import get_or_create_user_by_cookie
from apps.sibt.models     import VoteCounter
from util.consts          import *
from util.helpers         import generate_uuid
from util.model           import Model
from util.memcache_ref_prop import MemcacheReferenceProperty

NUM_VOTE_SHARDS = 15

# ------------------------------------------------------------------------------
# WOSIB Class Definition --------------------------------------------------------
# ------------------------------------------------------------------------------
class WOSIB(App):
    """Model storing the data for a client's WOSIB app"""

    store_name    = db.StringProperty( indexed = True )

    def __init__(self, *args, **kwargs):
        """ Initialize this model """
        super(WOSIB, self).__init__(*args, **kwargs)
    
    def handleLinkClick( self, urihandler, link ):
        logging.info("WOSIBAPP HANDLING LINK CLICK" )

        # Fetch User by cookie
        user = get_or_create_user_by_cookie( urihandler, self )

        # Create a ClickAction
        act = WOSIBClickAction.create( user, self, link )

        # Go to where the link points
        # Flag it so we know they came from the short link
        urihandler.redirect('%s#code=%s' % (link.target_url, link.willt_url_code))

    def create_instance(self, user, end, link, img, motivation=None, dialog=""):
        logging.info("MAKING A WOSIB INSTANCE")
        logging.debug("DIALOG %s" % dialog)
        # Make the properties
        uuid = generate_uuid( 16 )
        
        # Now, make the object
        instance = WOSIBInstance(key_name     = uuid,
                                uuid         = uuid,
                                asker        = user,
                                app_         = self,
                                link         = link,
                                product_img  = img,
                                motivation   = motivation,
                                url          = link.target_url)
        # set end if None
        if end == None:
            six_hours = timedelta(hours=6)
            end = instance.created + six_hours
        instance.end_datetime = end
        instance.special_put()
            
        # Now, make an action
        WOSIBInstanceCreated.create(user, instance=instance, medium=dialog)
        return instance

        @staticmethod
        def get_by_uuid( uuid ):
            return WOSIB.all().filter( 'uuid =', uuid ).get()

# Accessors --------------------------------------------------------------------

# ------------------------------------------------------------------------------
# WOSIBInstance Class Definition ------------------------------------------------
# ------------------------------------------------------------------------------
class WOSIBInstance(Model):
    # Unique identifier for memcache and DB key
    uuid            = db.StringProperty( indexed = True )

    # Datetime when this model was put into the DB
    created         = db.DateTimeProperty(auto_now_add=True)

    def __init__(self, *args, **kwargs):
        """ Initialize this model """
        self._memcache_key = kwargs['uuid'] 
        super(WOSIBInstance, self).__init__(*args, **kwargs)

    @staticmethod
    def get_by_uuid(uuid, only_live=True):
        return WOSIBInstance.get(uuid)

    def get_yesses_count(self):
        """Count this instance's yes count"""
        total = memcache.get(self.uuid+"VoteCounter_yesses")
        if total is None:
            total = 0
            for counter in VoteCounter.all().\
            filter('instance_uuid =', self.uuid).fetch( NUM_VOTE_SHARDS ):
                total += counter.yesses
            memcache.add(key=self.uuid+"VoteCounter_yesses", value=total)
        
        return total

    def get_nos_count(self):
        """Count this instance's no count"""
        total = memcache.get(self.uuid+"VoteCounter_nos")
        if total is None:
            total = 0
            for counter in VoteCounter.all().\
            filter('instance_uuid =', self.uuid).fetch( NUM_VOTE_SHARDS ):
                total += counter.nos
            memcache.add(key=self.uuid+"VoteCounter_nos", value=total)
        
        return total
    
    def increment_yesses(self):
        """Increment this instance's votes (yes) counter"""
        def txn():
            index = random.randint(0, NUM_VOTE_SHARDS-1)
            shard_name = self.uuid + str(index)
            counter = VoteCounter.get_by_key_name(shard_name)
            if counter is None:
                counter = VoteCounter(key_name      =shard_name, 
                                      instance_uuid=self.uuid)
            counter.yesses += 1
            counter.put()

        db.run_in_transaction(txn)
        memcache.incr(self.uuid+"VoteCounter_yesses")
    
    def increment_nos(self):
        """Increment this instance's votes (no) counter"""
        def txn():
            index = random.randint(0, NUM_VOTE_SHARDS-1)
            shard_name = self.uuid + str(index)
            counter = VoteCounter.get_by_key_name(shard_name)
            if counter is None:
                counter = VoteCounter(key_name      =shard_name, 
                                      instance_uuid=self.uuid)
            counter.nos += 1
            counter.put()

        db.run_in_transaction(txn)
        memcache.incr(self.uuid+"VoteCounter_nos")

# ------------------------------------------------------------------------------
# VoteCounter Class Definition ------------------------------------------------
# ------------------------------------------------------------------------------
class WOSIBVoteCounter(VoteCounter):
    """product-specific votes"""

    product_uuid = db.StringProperty(indexed=True, required=True)

# ------------------------------------------------------------------------------
# PartialWOSIBInstance Class Definition -----------------------------------------
# ------------------------------------------------------------------------------
class PartialWOSIBInstance(Model):
    ''' Each User can have at most 1 PartialInstance:
        - created when facebook connect starts
        - expires when user cancels facebook connect
        - deleted never
    '''
    
    uuid        = db.StringProperty( indexed = True )

    # User is the only index.
    user        = MemcacheReferenceProperty(db.Model, 
                                       collection_name='partial_wosib_instances',
                                       indexed=True)
    link        = db.ReferenceProperty(db.Model, 
                                       collection_name='link_partial_wosib_instances',
                                       indexed=False)
    
    # products are stored as 'uuid','uuid','uuid' because object lists aren't possible.
    products     = db.StringProperty(db.Text, indexed=True)
    
    app_        = db.ReferenceProperty( db.Model,
                                       collection_name='app_partial_wosib_instances',
                                       indexed=False)

    def __init__(self, *args, **kwargs):
        """ Initialize this model """
        self._memcache_key = kwargs['uuid'] 
        super(PartialWOSIBInstance, self).__init__(*args, **kwargs)

    """ Users can only have 1 of these ever.
        If they already have one, update it.
        Otherwise, make a new one. """
    @staticmethod
    def create( user, app, link, products ):

        instance = PartialWOSIBInstance.get_by_user( user )
        if instance:
            instance.link    = link
            # instance.product = product
            instance.app_    = app
        else: 
            uuid = generate_uuid( 16 )

            instance = PartialWOSIBInstance( key_name = uuid,
                                            uuid     = uuid,
                                            user     = user,
                                            link     = link, 
                                            products  = products, # type str
                                            app_     = app )
        instance.put()
        return instance

    @staticmethod
    def get_by_user( user ):
        return PartialWOSIBInstance.all().filter( 'user =', user ).get()
