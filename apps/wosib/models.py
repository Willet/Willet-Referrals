#!/usr/bin/python

# WOSIB model
# Extends from "App"

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc"

import hashlib
import logging
import random
from datetime                   import datetime
from datetime                   import timedelta

from django.utils               import simplejson as json
from google.appengine.api       import memcache
from google.appengine.ext       import db
from google.appengine.datastore import entity_pb

from apps.app.models            import App
from apps.email.models          import Email
from apps.link.models           import Link
from apps.product.models        import Product
from apps.user.models           import get_or_create_user_by_cookie
from apps.vote.models           import VoteCounter
from apps.wosib.actions         import *
from util.consts                import *
from util.helpers               import generate_uuid
from util.memcache_ref_prop     import MemcacheReferenceProperty
from util.model                 import Model

NUM_VOTE_SHARDS = 15

# ------------------------------------------------------------------------------
# WOSIB Class Definition --------------------------------------------------------
# ------------------------------------------------------------------------------
class WOSIB(App):
    """Model storing the data for a client's WOSIB app"""
    
    # stored as App

    store_name    = db.StringProperty( indexed = True )

    def __init__(self, *args, **kwargs):
        """ Initialize this model """
        super(WOSIB, self).__init__(*args, **kwargs)
    
    def handleLinkClick( self, urihandler, link ):
        logging.info("WOSIBAPP HANDLING LINK CLICK" )

        # Fetch User by cookie
        user = get_or_create_user_by_cookie( urihandler, self )

        # Create a ClickAction
        # act = WOSIBClickAction.create( user, self, link )

        # Go to where the link points
        # Flag it so we know they came from the short link
        logging.info ("%s = %s" % ('handleLinkClick' ,link.target_url))
        urihandler.redirect('%s#code=%s' % (link.target_url, link.willt_url_code))

    def create_instance(self, user, end, link, products):
        logging.info("MAKING A WOSIB INSTANCE")
        # Make the properties
        uuid = generate_uuid( 16 )
        
        # Now, make the object
        instance = WOSIBInstance(key_name     = uuid,
                                uuid         = uuid,
                                asker        = user,
                                app_         = self,
                                link         = link,
                                products     = products,
                                url          = link.target_url)
        # set end if None
        if end == None:
            six_hours = timedelta(hours=6)
            end = instance.created + six_hours
        instance.end_datetime = end
        instance.put()
            
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
    uuid = db.StringProperty( indexed = True )

    # Datetime when this model was put into the DB
    created = db.DateTimeProperty(auto_now_add = True, indexed = True)

    # The User who asked WOSIB to their friends
    asker = MemcacheReferenceProperty(db.Model, collection_name='wosib_instances' )

    # Parent App that "owns" these instances
    app_ = db.ReferenceProperty(db.Model, collection_name="app_wosib_instances" )

    link = db.ReferenceProperty(db.Model, collection_name='wosib_instance_links', indexed=False)

    # products are stored as 'uuid','uuid','uuid' because object lists aren't possible.
    products     = db.StringListProperty(db.Text, indexed=True)

    def __init__(self, *args, **kwargs):
        """ Initialize this model """
        self._memcache_key = kwargs['uuid'] 
        super(WOSIBInstance, self).__init__(*args, **kwargs)

    def get_winning_products (self):
        # returns an array of products with the most votes in the instance.
        # array can be of one item.
        
        # this list comprehension returns the number of votes (times chosen) for each product in the WOSIBInstance.
        instance_product_votes = [Action.\
                                    all().\
                                    filter('wosib_instance =', self).\
                                    filter('product_uuid =', product_uuid)\
                                    .count() for product_uuid in self.products] # [votes,votes,votes]
        logging.debug ("instance_product_votes = %r" % instance_product_votes)
        
        instance_product_dict = dict (zip (self.products, instance_product_votes)) # {uuid: votes, uuid: votes,uuid: votes}
        logging.debug ("instance_product_dict = %r" % instance_product_dict)
        
        if instance_product_votes.count(max(instance_product_votes)) > 1:
            # that is, if multiple items have the same score
            winning_products_uuids = filter(lambda x: instance_product_dict[x] == instance_product_votes[0], self.products)
            return Product\
                       .all()\
                       .filter('uuid IN', winning_products_uuids)\
                       .fetch(1000)
        else:
            # that is, if one product is winning the voting
            winning_product_uuid = self.products[instance_product_votes.index(max(instance_product_votes))]
            return [Product.all().filter('uuid =', winning_product_uuid).get()]
    
    def get_votes_count(self):
        """Count this instance's votes count
           For compatibility reasons, the field 'yesses' is used to keep count"""
        total = memcache.get(self.uuid+"WOSIBVoteCounter_count")
        if total is None:
            total = 0
            for counter in VoteCounter.all().\
            filter('instance_uuid =', self.uuid).fetch( NUM_VOTE_SHARDS ):
                total += counter.yesses
            memcache.add(key=self.uuid+"WOSIBVoteCounter_count", value=total)
        return total
    
    def increment_votes(self):
        """Increment this instance's votes counter
           For compatibility reasons, the field 'yesses' is used to keep count"""
        def txn():
            logging.info ("Running vote++ transaction")
            index = random.randint(0, NUM_VOTE_SHARDS-1)
            shard_name = self.uuid + str(index)
            counter = VoteCounter.get_by_key_name(shard_name)
            if counter is None:
                counter = VoteCounter(key_name      =shard_name, 
                                      instance_uuid=self.uuid)
            counter.yesses += 1
            counter.put()

        db.run_in_transaction(txn)
        memcache.incr(self.uuid+"WOSIBVoteCounter_count")
    

    @staticmethod
    def get_by_uuid(uuid):
        return WOSIBInstance.get(uuid)

    @staticmethod 
    def _get_from_datastore(uuid):
        return db.Query(WOSIBInstance).filter('uuid =', uuid).get()

    @staticmethod
    def get_by_link(link):
        return WOSIBInstance.all()\
                .filter('link =', link)\
                .get()

    @staticmethod
    def get_by_user_and_app (user, app_):
        # returns only the most recent instance.
        # function makes sense only when one instance is active per user per store.
        return WOSIBInstance.all()\
                .filter('asker =', user)\
                .filter('app_ =', app_)\
                .order('-created')\
                .get()
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

    user        = MemcacheReferenceProperty(db.Model, 
                                       collection_name='partial_wosib_instances',
                                       indexed=True)
    
    link        = db.ReferenceProperty(db.Model, 
                                       collection_name='link_partial_wosib_instances',
                                       indexed=False)
    
    # products are stored as 'uuid','uuid','uuid' because object lists aren't possible.
    products    = db.StringListProperty(db.Text, indexed=False)
    
    app_        = db.ReferenceProperty(db.Model,
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
            logging.info ("Updating existing PartialWOSIBInstance.")
            instance.link    = link
            instance.products = products
            instance.app_    = app
        else:
            # make a new one (user doesn't have an existing partial instance).
            uuid = generate_uuid( 16 )

            instance = PartialWOSIBInstance( key_name = uuid,
                                            uuid     = uuid,
                                            user     = user,
                                            link     = link, 
                                            products  = products, # type StringList
                                            app_     = app )
        instance.put()
        return instance

    @staticmethod
    def get_by_user( user ):
        return PartialWOSIBInstance.all().filter( 'user =', user ).get()

    @staticmethod
    def get_by_uuid(uuid):
        return PartialWOSIBInstance.get(uuid)

    @staticmethod 
    def _get_from_datastore(uuid):
        return db.Query(PartialWOSIBInstance).filter('uuid =', uuid).get()