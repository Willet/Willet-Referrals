#!/usr/bin/python

# SIBT model
# Extends from "App"

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc"

import hashlib, logging, datetime

from django.utils         import simplejson as json
from google.appengine.ext import db

from apps.action.models   import create_sibt_click_action
from apps.app.models      import App
from apps.link.models     import Link
from apps.user.models     import get_or_create_user_by_cookie

from util.consts          import *
from util.helpers         import generate_uuid
from util.model           import Model

NUM_VOTE_SHARDS = 15

# ------------------------------------------------------------------------------
# SIBT Class Definition --------------------------------------------------------
# ------------------------------------------------------------------------------
class SIBT( App ):
    """Model storing the data for a client's 'Should I Buy This?' app"""
    emailed_at_10 = db.BooleanProperty( default = False )
   
    store_name    = db.StringProperty( indexed = True )

    def __init__(self, *args, **kwargs):
        """ Initialize this model """
        super(SIBT, self).__init__(*args, **kwargs)
    
    def handleLinkClick( self, urihandler, link ):
        logging.info("SIBTAPP HANDLING LINK CLICK" )

        # Fetch User by cookie
        user = get_or_create_user_by_cookie( urihandler )

        # Create a ClickAction
        act = create_sibt_click_action( user, self, link )

        # Go to where the link points
        # Flag it so we know they came from the short link
        urihandler.redirect('%s?code=%s' % (link.target_url, link.willt_url_code))

    def create_instance( self, user, end, link ):
        # Make the properties
        uuid = generate_uuid( 16 )

        # Now, make the object
        instance = SIBTInstance( key_name     = uuid,
                                 uuid         = uuid,
                                 asker        = user,
                                 app_         = self,
                                 end_datetime = end,
                                 link         = link,
                                 url          = link.target_url )
        instance.put()
        
        return instance

# Accessors --------------------------------------------------------------------

# ------------------------------------------------------------------------------
# SIBTInstance Class Definition ------------------------------------------------
# ------------------------------------------------------------------------------
class SIBTInstance( Model ):
    # Unique identifier for ndlmemcache and DB key
    uuid            = db.StringProperty( indexed = True )

    # Datetime when this model was put into the DB
    created         = db.DateTimeProperty( auto_now_add=True )
    
    # The User who asked SIBT to their friends?
    asker           = db.ReferenceProperty( db.Model, collection_name='sibt_instances' )
   
    # Parent App that "owns" these instances
    app_            = db.ReferenceProperty( db.Model, collection_name="instances" )

    # The Link for this instance (1 per instance)
    link            = db.ReferenceProperty( db.Model, collection_name="sibt_instance" )
    
    # URL of the Link (here for quick filter)
    url             = db.LinkProperty  ( indexed = True )
    
    # URL of the product image
    product_img     = db.LinkProperty  ( indexed = False )
    
    # Datetime when this instance should shut down and email asker 
    end_datetime    = db.DateTimeProperty( )

    # True iff end_datetime < now. False, otherwise.
    is_live         = db.BooleanProperty( default = True )

    def __init__(self, *args, **kwargs):
        """ Initialize this model """
        self._memcache_key = kwargs['uuid'] 
        super(SIBTInstance, self).__init__(*args, **kwargs)
    
    def get_yesses_count(self):
        """Count this instance's yes count"""
        
        total = memcache.get(self.uuid+"VoteCounter_yesses")
        if total is None:
            total = 0
            for counter in VoteCounter.all().\
            filter('instance_uuid =', self.uuid).fetch( NUM_VOTE_SHARES ):
                total += counter.yesses
            memcache.add(key=self.uuid+"VoteCounter_yesses", value=total)
        
        return total

    def get_nos_count(self):
        """Count this instance's no count"""
        
        total = memcache.get(self.uuid+"VoteCounter_nos")
        if total is None:
            total = 0
            for counter in VoteCounter.all().\
            filter('instance_uuid =', self.uuid).fetch( NUM_VOTE_SHARES ):
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

# Accessor ---------------------------------------------------------------------
def get_sibt_instance_by_asker_for_url( user, url ):
    return SIBTInstance.all().filter( 'asker = ', user ).filter( 'url = ', url ).get()

def get_sibt_instance_by_link( link ):
    return SIBTInstance.all().filter( 'link =', link ).get()

def get_sibt_instance_by_uuid( uuid ):
    return SIBTInstance.all().filter( 'uuid =', uuid ).get()

# ------------------------------------------------------------------------------
# SIBTInstance Class Definition ------------------------------------------------
# ------------------------------------------------------------------------------

class VoteCounter(db.Model):
    """Sharded counter for voting counts"""

    instance_uuid = db.StringProperty(indexed=True, required=True)
    yesses        = db.IntegerProperty(indexed=False, required=True, default=0)
    nos           = db.IntegerProperty(indexed=False, required=True, default=0)
