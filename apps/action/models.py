#!/usr/bin/python

# The Action Model
# A parent class for all User actions 
# ie. ClickAction, VoteAction, ViewAction, etc

__author__    = "Willet, Inc."
__copyright__ = "Copyright 2011, Willet, Inc"

import datetime, logging

from google.appengine.api    import memcache, taskqueue
from google.appengine.ext    import db
from google.appengine.ext.db import polymodel

from util.consts             import *
from util.helpers            import generate_uuid
from util.model              import Model

## -----------------------------------------------------------------------------
## Action SuperClass -----------------------------------------------------------
## -----------------------------------------------------------------------------
class Action( Model, polymodel.PolyModel ):
    """ Whenever a 'User' completes a Willet Action,
        an 'Action' obj will be stored for them.
        This 'Action' class will be subclassed for specific actions
        ie. click, vote, tweet, share, email, etc. """

    # Unique identifier for memcache and DB key
    uuid            = db.StringProperty( indexed = True )
    
    # Datetime when this model was put into the DB
    created         = db.DateTimeProperty( auto_now_add=True )
    
    # Person who did the action
    user            = db.ReferenceProperty( db.Model, collection_name = 'actions' )
    
    # The Action that this Action is for
    app_            = db.ReferenceProperty( db.Model, collection_name = 'user_actions' )
    
    # Link that caused the action ...
    link            = db.ReferenceProperty( db.Model, collection_name = "link_actions" )
    
    def __init__(self, *args, **kwargs):
        self._memcache_key = kwargs['uuid'] if 'uuid' in kwargs else None 
        super(Action, self).__init__(*args, **kwargs)
    
    @staticmethod
    def _get_from_datastore(uuid):
        """Datastore retrieval using memcache_key"""
        return Action.all().filter('uuid =', uuid).get()

    def validateSelf( self ):
        if self.user.is_admin():
            return True # Anything except None

    def __unicode__(self):
        return self.__str__()

    def __str__(self):
        # Subclasses should override this
        pass

## Accessors -------------------------------------------------------------------
def get_action_by_uuid( uuid ):
    return Action.all().filter( 'uuid =', uuid ).get()

def get_actions_by_user( user ):
    return Action.all().filter( 'user =', user ).get()

def get_actions_by_app( app ):
    return Action.all().filter( 'app =', app ).get()

def get_actions_by_user_for_app( user, app ):
    return Action.all().filter( 'user =', user).filter( 'app =', app ).get()

## -----------------------------------------------------------------------------
## ClickAction Subclass --------------------------------------------------------
## -----------------------------------------------------------------------------
class ClickAction( Action ):
    """ Designates a 'click' action for a User. 
        Currently used for 'Referral' and 'SIBT' Apps """
    
    def __init__(self, *args, **kwargs):
        super(ClickAction, self).__init__(*args, **kwargs)

        # Tell Mixplanel that we got a click
        self.app_.storeAnalyticsDatum( self.class_name(), self.user, self.link.target_url )
           
    def __str__(self):
        return 'CLICK: %s(%s) %s' % (
                self.user.get_full_name(),
                self.user.uuid,
                self.app_.uuid
        )

def create_click_action( user, app, link ):
    # Make the action
    uuid = generate_uuid( 16 )
    act  = ClickAction( key_name = uuid,
                        uuid     = uuid,
                        user     = user,
                        app_     = app,
                        link     = link )
    act.put()
   
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

def create_sibt_click_action( user, app, link ):
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


## Accessors -------------------------------------------------------------------
def get_sibt_click_actions_by_user_for_url(user, url):
    return SIBTClickAction.all()\
            .filter('user =', user)\
            .filter('url =', url)

def get_sibt_click_actions_by_user_and_link(user, url):
    return SIBTClickAction.all()\
            .filter('user =', user)\
            .filter('url =', url)

## -----------------------------------------------------------------------------
## VoteAction Subclass ---------------------------------------------------------
## -----------------------------------------------------------------------------
class VoteAction( Action ):
    """ Designates a 'vote' action for a User.
        Primarily used for 'SIBT' App """
    
    def __init__(self, *args, **kwargs):
        super(VoteAction, self).__init__(*args, **kwargs)
        
        # Tell Mixplanel that we got a vote
        self.app_.storeAnalyticsDatum( self.class_name(), self.user, self.link.target_url )
    
    def __str__(self):
        return 'VOTE: %s(%s) %s' % (self.user.get_full_name(), self.user.uuid, self.app_.uuid)

def create_vote_action( user, app, link ):
    # Make the action
    uuid = generate_uuid( 16 )
    act  = VoteAction( key_name = uuid,
                       uuid     = uuid,
                       user     = user,
                       app_     = app,
                       link     = link )
    act.put() 

## -----------------------------------------------------------------------------
## SIBTVoteAction Subclass ----------------------------------------------------
## -----------------------------------------------------------------------------
class SIBTVoteAction( VoteAction ):
    """ Designates a 'vote' action for a User on a SIBT instance. 
        Currently used for 'SIBT' App """

    sibt_instance = db.ReferenceProperty( db.Model, collection_name="vote_actions" )

    # URL that was voted on
    url = db.LinkProperty( indexed = True )

    def __str__(self):
        return 'SIBTVOTE: %s(%s) %s' % (self.user.get_full_name(), self.user.uuid, self.app_.uuid)

def create_sibt_vote_action( user, instance ):
    # Make the action
    uuid = generate_uuid( 16 )
    act  = SIBTVoteAction(  key_name = uuid,
                            uuid     = uuid,
                            user     = user,
                            app_     = instance.app_,
                            link     = instance.link,
                            url      = instance.link.target_url,
                            sibt_instance = instance )
    act.put()
