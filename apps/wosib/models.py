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
from apps.sibt.models     import VoteCounter
from apps.user.models     import get_or_create_user_by_cookie
from apps.wosib.actions   import *
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
    created = db.DateTimeProperty(auto_now_add=True)

    # The User who asked WOSIB to their friends
    asker = MemcacheReferenceProperty(db.Model, collection_name='wosib_instances' )

    # Parent App that "owns" these instances
    app_ = db.ReferenceProperty(db.Model, collection_name="wosib_app_instances" )

    link = db.ReferenceProperty(db.Model, collection_name='link_wosib_instances', indexed=False)

    # the number of times this instance had received votes
    # (less accurate than WOSIBVoteAction.all().filter('wosib_instance =', instance).count(),
    # but saves DB reads. See DoWOSIBVote for property incrementation.)
    votes = db.IntegerProperty (default = 0, indexed = False)

    # products are stored as 'uuid','uuid','uuid' because object lists aren't possible.
    products     = db.StringListProperty(db.Text, indexed=True)

    def __init__(self, *args, **kwargs):
        """ Initialize this model """
        self._memcache_key = kwargs['uuid'] 
        super(WOSIBInstance, self).__init__(*args, **kwargs)

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
    def get_by_user(user):
        # returns only the most recent instance.
        return WOSIBInstance.all()\
                .filter('asker =', user)\
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
