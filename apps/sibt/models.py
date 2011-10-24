#!/usr/bin/python

# SIBT model
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

from apps.sibt.actions          import SIBTClickAction
from apps.app.models      import App
from apps.email.models    import Email
from apps.gae_bingo.gae_bingo import bingo
from apps.link.models     import Link
from apps.user.models     import get_or_create_user_by_cookie

from util.consts          import *
from util.helpers         import generate_uuid
from util.model           import Model

NUM_VOTE_SHARDS = 15

# ------------------------------------------------------------------------------
# SIBT Class Definition --------------------------------------------------------
# ------------------------------------------------------------------------------
class SIBT(App):
    """Model storing the data for a client's 'Should I Buy This?' app"""
    emailed_at_10 = db.BooleanProperty( default = False )
   
    store_name    = db.StringProperty( indexed = True )
    #store_url     = db.LinkProperty( indexed = False, default = None, required = False )

    # Div IDs or class names
    buy_btn_id    = db.StringProperty( indexed = True )

    def __init__(self, *args, **kwargs):
        """ Initialize this model """
        super(SIBT, self).__init__(*args, **kwargs)
    
    def handleLinkClick( self, urihandler, link ):
        logging.info("SIBTAPP HANDLING LINK CLICK" )

        # Fetch User by cookie
        user = get_or_create_user_by_cookie( urihandler )

        # Create a ClickAction
        act = SIBTClickAction.create( user, self, link )

        # GAY BINGO!
        if not user.is_admin():
            bingo( 'sibt_share_text2' )

        # Go to where the link points
        # Flag it so we know they came from the short link
        urihandler.redirect('%s#code=%s' % (link.target_url, link.willt_url_code))

    def create_instance(self, user, end, link, img):
        logging.info("MAKING A SIBT INSTANCE")
        # Make the properties
        uuid = generate_uuid( 16 )
        
        # set end if None
        if end == None:
            now = datetime.now()
            six_hours = timedelta(hours=6)
            end = now + six_hours
        
        # Now, make the object
        instance = SIBTInstance( key_name     = uuid,
                                 uuid         = uuid,
                                 asker        = user,
                                 app_         = self,
                                 end_datetime = end,
                                 link         = link,
                                 product_img  = img,
                                 url          = link.target_url )
        instance.put()
        
        # GAY BINGO
        if not user.is_admin():
            bingo( 'sibt_share_text2' )

        if not user.is_admin() and "social-referral" in URL:
            try:
                Email.emailBarbara("""
                    SIBT INSTANCE:<br />
                    uuid= %s<br />
                    user.key= %s<br />
                    page= %s<br />
                    link= http://rf.rs/%s<br />
                    name= %s<br />
                    fb_uuid= %s<br />
                    fb_access_token= %s <br \>
                    <a href='https://graph.facebook.com/%s?access_token=%s'>FB Profile</a>
                    """ % (
                        uuid,
                        user.key(), 
                        link.target_url,
                        link.willt_url_code,
                        user.get_full_name(),
                        user.get_attr('fb_identity'),
                        user.get_attr('fb_access_token'),
                        user.get_attr('fb_identity'),
                        user.get_attr('fb_access_token')
                    )
                )
            except Exception, e:
               Email.emailBarbara('SIBT INSTANCE: error printing data: %s' % str(e))
        return instance

# Accessors --------------------------------------------------------------------

# ------------------------------------------------------------------------------
# SIBTInstance Class Definition ------------------------------------------------
# ------------------------------------------------------------------------------
class SIBTInstance( Model ):
    # Unique identifier for memcache and DB key
    uuid            = db.StringProperty( indexed = True )

    # Datetime when this model was put into the DB
    created         = db.DateTimeProperty(auto_now_add=True)
    
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
    end_datetime    = db.DateTimeProperty()

    # True iff end_datetime < now. False, otherwise.
    is_live         = db.BooleanProperty( default = True )

    def __init__(self, *args, **kwargs):
        """ Initialize this model """
        self._memcache_key = kwargs['uuid'] 
        super(SIBTInstance, self).__init__(*args, **kwargs)

    @staticmethod 
    def _get_from_datastore(uuid):
        return db.Query(SIBTInstance).filter('uuid =', uuid).get()

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

# Accessor ---------------------------------------------------------------------
def get_sibt_instance_by_asker_for_url(user, url, only_live=True):
    return SIBTInstance.all()\
            .filter('is_live =', only_live)\
            .filter('asker =', user)\
            .filter('url =', url)\
            .get()

def get_sibt_instance_by_link(link, only_live=True):
    return SIBTInstance.all()\
            .filter('is_live =', only_live)\
            .filter('link =', link)\
            .get()

def get_sibt_instance_by_uuid(uuid, only_live=True):
    return SIBTInstance.all()\
            .filter('is_live =', only_live)\
            .filter('uuid =', uuid)\
            .get()

# ------------------------------------------------------------------------------
# SIBTInstance Class Definition ------------------------------------------------
# ------------------------------------------------------------------------------

class VoteCounter(db.Model):
    """Sharded counter for voting counts"""

    instance_uuid = db.StringProperty(indexed=True, required=True)
    yesses        = db.IntegerProperty(indexed=False, required=True, default=0)
    nos           = db.IntegerProperty(indexed=False, required=True, default=0)

