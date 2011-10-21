#!/usr/bin/env/python

# Actions for SIBT
# SIBTClickAction, 
__author__    = "Willet, Inc."
__copyright__ = "Copyright 2011, Willet, Inc"

import datetime
import logging

from google.appengine.api   import memcache
from google.appengine.ext   import db

from apps.action.models     import ClickAction
from apps.action.models     import VoteAction

from util.helpers           import generate_uuid

## -----------------------------------------------------------------------------
## SIBTClickAction Subclass ----------------------------------------------------
## -----------------------------------------------------------------------------
class SIBTClickAction( ClickAction ):
    """ Designates a 'click' action for a User on a SIBT instance. 
        Currently used for 'Referral' and 'SIBT' Apps """

    sibt_instance = db.ReferenceProperty( db.Model, collection_name="click_actions" )

    # URL that was clicked on
    url           = db.LinkProperty( indexed = True )

    def __str__(self):
        return 'SIBTCLICK: %s(%s) %s' % (self.user.get_full_name(), self.user.uuid, self.app_.uuid)

    ## Constructor 
    @staticmethod
    def create( user, app, link ):
        # Make the action
        uuid = generate_uuid( 16 )
        act  = SIBTClickAction( key_name = uuid,
                                uuid = uuid,
                                user = user,
                                app_ = app,
                                link = link,
                                url = link.target_url,
                                sibt_instance = link.sibt_instance.get() )
        act.put()

    ## Accessors 
    @staticmethod
    def get_by_user_and_url(user, url):
        return SIBTClickAction.all()\
                .filter('user =', user)\
                .filter('url =', url)

    @staticmethod
    def get_by_instance( instance ):
        return SIBTClickAction.all().filter( 'sibt_instance =', instance )


## -----------------------------------------------------------------------------
## SIBTVoteAction Subclass ----------------------------------------------------
## -----------------------------------------------------------------------------
class SIBTVoteAction( VoteAction ):
    """ Designates a 'vote' action for a User on a SIBT instance. 
        Currently used for 'SIBT' App """

    sibt_instance = db.ReferenceProperty( db.Model, collection_name="vote_actions" )

    # URL that was voted on
    url           = db.LinkProperty( indexed = True )

    ## Constructor
    def create( user, instance, vote ):
        # Make the action
        uuid = generate_uuid( 16 )
        act  = SIBTVoteAction(  key_name = uuid,
                                uuid     = uuid,
                                user     = user,
                                app_     = instance.app_,
                                link     = instance.link,
                                url      = instance.link.target_url,
                                sibt_instance = instance,
                                vote     = vote )
        act.put()
    
    def __str__(self):
        return 'SIBTVOTE: %s(%s) %s' % (self.user.get_full_name(), self.user.uuid, self.app_.uuid)

    ## Accessors 
    @staticmethod
    def get_by_instance( instance ):
        return SIBTVoteAction.all().filter( 'sibt_instance =', instance )

    @staticmethod
    def get_by_app_and_instance_and_user( a, i, u ):
        return SIBTVoteAction.all().filter('app_ =', a)\
                                   .filter('sibt_instance =', i)\
                                   .filter('user =', u)\
                                   .get()

    @staticmethod
    def get_by_app_and_instance( a, i ):
        return SIBTVoteAction.all().filter('app_ =', a)\
                                   .filter('sibt_instance =', i).get()
