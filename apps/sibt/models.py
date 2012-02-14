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
from google.appengine.datastore import entity_pb

from apps.sibt.actions    import SIBTClickAction
from apps.sibt.actions    import SIBTInstanceCreated
from apps.app.models      import App
from apps.email.models    import Email
from apps.gae_bingo.gae_bingo import bingo
from apps.link.models     import Link
from apps.user.models     import get_or_create_user_by_cookie
from apps.vote.models     import VoteCounter

from util.consts          import *
from util.helpers         import generate_uuid
from util.model           import Model
from util.memcache_ref_prop import MemcacheReferenceProperty

NUM_VOTE_SHARDS = 15

# ------------------------------------------------------------------------------
# SIBT Class Definition --------------------------------------------------------
# ------------------------------------------------------------------------------
class SIBT(App):
    """Model storing the data for a client's 'Should I Buy This?' app"""
    
    # if the button is enabled for this app
    button_enabled = db.BooleanProperty(default=True)
    
    # if the top bar is enabled for this app 
    top_bar_enabled = db.BooleanProperty(default=True)

    # if incentivized asks is enabled
    incentive_enabled = db.BooleanProperty(default=False)

    # number of times a user has to view the page before
    # we show the top bar
    num_shows_before_tb = db.IntegerProperty(default=1)

    # Name of the store - used here for caching purposes.
    store_name    = db.StringProperty( indexed = True )

    def __init__(self, *args, **kwargs):
        """ Initialize this model """
        super(SIBT, self).__init__(*args, **kwargs)
    
    def handleLinkClick( self, urihandler, link ):
        logging.info("SIBTAPP HANDLING LINK CLICK" )

        # Fetch User by cookie
        user = get_or_create_user_by_cookie( urihandler, self )

        # Create a ClickAction
        act = SIBTClickAction.create( user, self, link )

        # GAY BINGO!
        if not user.is_admin():
            bingo( 'sibt_share_text3' )

        # Go to where the link points
        # Flag it so we know they came from the short link
        urihandler.redirect('%s#code=%s' % (link.target_url, link.willt_url_code))

    def create_instance(self, user, end, link, img, motivation=None, dialog=""):
        logging.info("MAKING A SIBT INSTANCE")
        logging.debug("DIALOG %s" % dialog)
        # Make the properties
        uuid = generate_uuid( 16 )
        
        # Now, make the object
        instance = SIBTInstance(key_name     = uuid,
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
        logging.info('instance created: %s\nends: %s' % (instance.created, instance.end_datetime))
        instance.special_put()
            
        # Now, make an action
        SIBTInstanceCreated.create(user, instance=instance, medium=dialog)
        
        # GAY BINGO
        if not user.is_admin():
            bingo( 'sibt_share_text3' )

        if not user.is_admin() and "social-referral" in URL:
            try:
                Email.emailBarbara("""
                    SIBT INSTANCE:<br />
                    dialog = %s <br />
                    uuid= %s<br />
                    user.key= %s<br />
                    page= %s<br />
                    link= http://rf.rs/%s<br />
                    name= %s<br />
                    fb_uuid= %s<br />
                    fb_access_token= %s <br />
                    <a href='https://graph.facebook.com/%s?access_token=%s'>FB Profile</a>
                    """ % (
                        dialog,
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

        @staticmethod
        def get_by_uuid( uuid ):
            return SIBT.all().filter( 'uuid =', uuid ).get()

# Accessors --------------------------------------------------------------------

# ------------------------------------------------------------------------------
# SIBTInstance Class Definition ------------------------------------------------
# ------------------------------------------------------------------------------
class SIBTInstance(Model):
    # Unique identifier for memcache and DB key
    uuid            = db.StringProperty( indexed = True )

    # the users motivation for sharing
    motivation = db.StringProperty(default="")

    # Datetime when this model was put into the DB
    created         = db.DateTimeProperty(auto_now_add=True)
    
    # The User who asked SIBT to their friends?
    asker           = MemcacheReferenceProperty( db.Model, collection_name='sibt_instances' )
   
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

    def special_put(self):
        """So we memcache by asker_uuid and url as well"""
        logging.info('enhanced SIBTShopify put')
        super(SIBTInstance, self).put()
        self.memcache_by_asker_and_url()

    def memcache_by_asker_and_url(self):
        return memcache.set(
                '%s-%s' % (self.asker.uuid, self.url), 
                db.model_to_protobuf(self).Encode(), time=MEMCACHE_TIMEOUT)
    
    @staticmethod 
    def _get_from_datastore(uuid):
        return db.Query(SIBTInstance).filter('uuid =', uuid).get()

    # Accessor ---------------------------------------------------------------------
    @staticmethod
    def get_by_asker_for_url(user, url, only_live=True):
        data = memcache.get('%s-%s' % (user.uuid, url))
        if data:
            instance = db.model_from_protobuf(entity_pb.EntityProto(data))
        else:
            instance = SIBTInstance.all()\
                .filter('is_live =', only_live)\
                .filter('asker =', user)\
                .filter('url =', db.Link(url))\
                .get()
            if instance:
                instance.memcache_by_asker_and_url()
        return instance

    @staticmethod
    def get_by_link(link, only_live=True):
        return SIBTInstance.all()\
                .filter('is_live =', only_live)\
                .filter('link =', link)\
                .get()

    @staticmethod
    def get_by_uuid(uuid, only_live=True):
        #return SIBTInstance.all()\
        #        .filter('is_live =', only_live)\
        #        .filter('uuid =', uuid)\
        #        .get()
        return SIBTInstance.get(uuid)

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
# PartialSIBTInstance Class Definition -----------------------------------------
# ------------------------------------------------------------------------------
class PartialSIBTInstance(Model):
    '''
    https://github.com/train07/Willet-Referrals/commit/812ab6bd76b9737a1e83d84055b1fe19947e91d4#commitcomment-851293
    Whenever someone doesn't FB connect, we start a PartialInstance and open up 
    a FB dialog. We don't know if they actually pushed the message to FB or not,
    right? This is why it's only a Partial Instance. When the User is redirected
    to our "Thanks" screen, we complete the partialinstance and make a full one
    and delete the partial one. If the person cancels, the PartialInstance is 
    deleted. If the person closes the window, the PartialInstance stays, but
    ... "expires".
    Each User can have at most 1 PartialInstance.
    '''
    
    uuid        = db.StringProperty( indexed = True )

    # User is the only index.
    user        = MemcacheReferenceProperty(db.Model, 
                                       collection_name='partial_sibt_instances',
                                       indexed=True)
    link        = db.ReferenceProperty(db.Model, 
                                       collection_name='link_partial_sibt_instances',
                                       indexed=False)
    product     = db.ReferenceProperty(db.Model, 
                                       collection_name='product_partial_sibt_instances',
                                       indexed=False)
    app_        = db.ReferenceProperty( db.Model,
                                       collection_name='app_partial_sibt_instances',
                                       indexed=False)

    def __init__(self, *args, **kwargs):
        """ Initialize this model """
        self._memcache_key = kwargs['uuid'] 
        super(PartialSIBTInstance, self).__init__(*args, **kwargs)

    """ Users can only have 1 of these ever.
        If they already have one, update it.
        Otherwise, make a new one. """
    @staticmethod
    def create( user, app, link, product ):

        instance = PartialSIBTInstance.get_by_user( user )
        if instance:
            instance.link    = link
            instance.product = product
            instance.app_    = app
        else: 
            uuid = generate_uuid( 16 )

            instance = PartialSIBTInstance( key_name = uuid,
                                            uuid     = uuid,
                                            user     = user,
                                            link     = link, 
                                            product  = product,
                                            app_     = app )
        instance.put()
        return instance

    @staticmethod
    def get_by_user( user ):
        return PartialSIBTInstance.all().filter( 'user =', user ).get()
