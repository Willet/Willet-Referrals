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

    def __str__(self):
        return 'CLICK: %s(%s) %s' % (self.user.get_full_name(), self.user.uuid, self.app.uuid)

    def create_click_action( user, app, link ):
        # Make the action
        uuid = generate_uuid( 16 )
        act  = ClickAction( key_name = uuid,
                            uuid     = uuid,
                            user     = user,
                            app      = app,
                            link     = link )
        act.put()

        # Tell Mixplanel that we got a click
        taskqueue.add( queue_name = 'mixpanel', 
                       url        = '/mixpanel', 
                       params     = {'event'    : 'Clicks', 
                                     'app_uuid' : app.uuid } )

        return act
        
## -----------------------------------------------------------------------------
## VoteAction Subclass ---------------------------------------------------------
## -----------------------------------------------------------------------------
class VoteAction( Action ):
    """ Designates a 'vote' action for a User.
        Primarily used for 'SIBT' App """
    
    def __str__(self):
        return 'VOTE: %s(%s) %s' % (self.user.get_full_name(), self.user.uuid, self.app.uuid)

    def create_vote_action( user, app, link ):
        # Make the action
        uuid = generate_uuid( 16 )
        act  = VoteAction( key_name = uuid,
                           uuid     = uuid,
                           user     = user,
                           app      = app,
                           link     = link )
        act.put() 

        # Tell Mixplanel that we got a vote
        taskqueue.add( queue_name = 'mixpanel', 
                       url        = '/mixpanel', 
                       params     = {'event'    : 'Votes', 
                                     'app_uuid' : app.uuid } )

        return act
