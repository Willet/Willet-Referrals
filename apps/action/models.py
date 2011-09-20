#!/usr/bin/python

# The Action Model
# A parent class for all User actions 
# ie. ClickAction, VoteAction, ViewAction, etc

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc"

import datetime, logging

from google.appengine.api    import memcache
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
    app             = db.ReferenceProperty( db.Model, collection_name = 'user_actions' )
    
    # Link that caused the action ...
    link            = db.ReferenceProperty( db.Model, collection_name = "link_actions" )
    
    def __init__(self, *args, **kwargs):
        self._memcache_key = kwargs['uuid'] if 'uuid' in kwargs else None 
        super(Action, self).__init__(*args, **kwargs)
    
    @staticmethod
    def _get_from_datastore(uuid):
        """Datastore retrieval using memcache_key"""
        return Action.all().filter('uuid =', uuid).get()

    def toString( self ):
        # Subclasses should override this
        return

## Accessors -------------------------------------------------------------------
def get_action_by_uuid( uuid ):
    return Action.all().filter( 'uuid =', uuid ).get()

def get_actions_by_user( user ):
    return Action.all().filter( 'user =', user ).get()

def get_actions_by_app( app ):
    return Action.all().filter( 'app =', app ).get()

def get_actions_by_user_for_app( app, user ):
    return Action.all().filter( 'user =', user).filter( 'app =', app ).get()


## -----------------------------------------------------------------------------
## ClickAction Subclass --------------------------------------------------------
## -----------------------------------------------------------------------------
class ClickAction( Action ):
    """ Designates a 'click' action for a User. 
        Currently used for 'Referral' and 'SIBT' Apps """

    def __init__(self, *args, **kwargs):
        self._memcache_key = kwargs['uuid'] if 'uuid' in kwargs else None 
        super(ClickAction, self).__init__(*args, **kwargs)

## -----------------------------------------------------------------------------
## VoteAction Subclass ---------------------------------------------------------
## -----------------------------------------------------------------------------
class VoteAction( Action ):
    """ Designates a 'vote' action for a User.
        Primarily used for 'SIBT' App """

    def __init__(self, *args, **kwargs):
        self._memcache_key = kwargs['uuid'] if 'uuid' in kwargs else None 
        super(VoteAction, self).__init__(*args, **kwargs)
