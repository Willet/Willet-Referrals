#!/usr/bin/python

# The Action Model
# A parent class for all User actions 
# ie. ClickAction, VoteAction, ViewAction, etc

__author__    = "Willet, Inc."
__copyright__ = "Copyright 2011, Willet, Inc"

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
    user            = db.ReferenceProperty( db.Model, collection_name = 'user_actions' )
    
    # True iff this Action's User is an admin
    is_admin        = db.BooleanProperty( default = False )
    
    # The Action that this Action is for
    app_            = db.ReferenceProperty( db.Model, collection_name = 'app_actions' )
    
    def __init__(self, *args, **kwargs):
        self._memcache_key = kwargs['uuid'] if 'uuid' in kwargs else None 

        if kwargs['user'].is_admin():
            kwargs['is_admin'] = True

        super(Action, self).__init__(*args, **kwargs)
    
    @staticmethod
    def _get_from_datastore(uuid):
        """Datastore retrieval using memcache_key"""
        return Action.all().filter('uuid =', uuid).get()

    def validateSelf( self ):
        pass
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
    return Action.all().filter( 'app_ =', app ).get()

def get_actions_by_user_for_app( user, app ):
    return Action.all().filter( 'user =', user).filter( 'app_ =', app ).get()

## -----------------------------------------------------------------------------
## ClickAction Subclass --------------------------------------------------------
## -----------------------------------------------------------------------------
class ClickAction( Action ):
    """ Designates a 'click' action for a User. 
        Currently used for 'Referral' and 'SIBT' Apps """
    
    # Link that caused the click action ...
    link = db.ReferenceProperty( db.Model, collection_name = "link_clicks" )
    
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

## Constructor -----------------------------------------------------------------
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
## VoteAction Subclass ---------------------------------------------------------
## -----------------------------------------------------------------------------
class VoteAction( Action ):
    """ Designates a 'vote' action for a User.
        Primarily used for 'SIBT' App """
    
    # Link that caused the vote action ...
    link = db.ReferenceProperty( db.Model, collection_name = "link_votes" )

    # Either 'yes' or 'no'
    vote = db.StringProperty( indexed = True )
    
    def __init__(self, *args, **kwargs):
        super(VoteAction, self).__init__(*args, **kwargs)
        
        # Tell Mixplanel that we got a vote
        self.app_.storeAnalyticsDatum( self.class_name(), self.user, self.link.target_url )
    
    def __str__(self):
        return 'VOTE: %s(%s) %s' % (self.user.get_full_name(), self.user.uuid, self.app_.uuid)

    def validateSelf( self ):
        if not ( self.vote == 'yes' or self.vote == 'no' ):
            raise Exception("Vote type needs to be yes or no")

    @staticmethod
    def get_by_vote( vote ):
        return VoteAction.all().filter( 'vote =', vote )

    @staticmethod
    def get_all_yesses( ):
        return VoteAction.all().filter( 'vote =', 'yes' )

    @staticmethod
    def get_all_nos( ):
        return VoteAction.all().filter( 'vote =', 'no' )

## Constructor -----------------------------------------------------------------
def create_vote_action( user, app, link, vote ):
    # Make the action
    uuid = generate_uuid( 16 )
    act  = VoteAction( key_name = uuid,
                       uuid     = uuid,
                       user     = user,
                       app_     = app,
                       link     = link,
                       vote     = vote )
    act.put() 

## -----------------------------------------------------------------------------
## PageView Subclass -----------------------------------------------------------
## -----------------------------------------------------------------------------
class PageView( Action ):
    """ Designates a 'page view' for a User. """

    url = db.LinkProperty( indexed = True )

    def __str__(self):
        return 'PageView: %s(%s) %s' % (self.user.get_full_name(), self.user.uuid, self.app_.uuid)

    ## Constructor 
    @staticmethod
    def create( user, app, url ):
    uuid = generate_uuid( 16 )
    act  = PageView( key_name = uuid,
                     uuid     = uuid,
                     user     = user,
                     app_     = app,
                     url      = url )
    act.put()

## Accessors -------------------------------------------------------------------
def get_pageviews_by_url( url ):
    return PageView.all().filter( 'url =', url )

def get_pageviews_by_user_and_url( user, url ):
    return PageView.all().filter( 'user = ', user ).filter( 'url =', url )

## -----------------------------------------------------------------------------
## GaeBingoAlt Subclass --------------------------------------------------------
## -----------------------------------------------------------------------------
class GaeBingoAlt( Action ):
    """ Stores the variation that a given User sees"""
    conversion_name = db.StringProperty( indexed = True )
    alt             = db.StringProperty( indexed = False )

    def __str__(self):
        return 'GaeBingoAlt: %s(%s) %s: %s' % ( self.user.get_full_name(), 
                                                self.user.uuid, 
                                                self.conversion_name,
                                                self.alt )

## Constructor -----------------------------------------------------------------
def create_gaebingo_alt( user, app, conversion_name, alt ):
    act = get_gaebingo_alt_for_user_and_conversion( user, conversion_name )

    if act.count() == 0:
        uuid = generate_uuid( 16 )
        act  = GaeBingoAlt( key_name = uuid,
                            uuid     = uuid,
                            user     = user,
                            app_     = app,
                            conversion_name = conversion_name,
                            alt      = alt )
        act.put()

## Accessors  -----------------------------------------------------------------
def get_gaebingo_alt_for_user_and_conversion( user, conversion ):
    return GaeBingoAlt.all().filter( 'user =', user ).filter( 'conversion_name =', conversion )


## -----------------------------------------------------------------------------
## WantAction Subclass --------------------------------------------------------
## -----------------------------------------------------------------------------
class WantAction( Action ):
    """ Stored if a User wants an item. """
    
    # Link that caused the want action ...
    link = db.ReferenceProperty( db.Model, collection_name = "link_wants" )
    
    def __str__(self):
        return 'Want: %s(%s) %s' % (
                self.user.get_full_name(),
                self.user.uuid,
                self.app_.uuid
        )

## Constructor -----------------------------------------------------------------
def create_want_action( user, app, link ):
    # Make the action
    uuid = generate_uuid( 16 )
    act  = WantAction( key_name = uuid,
                       uuid     = uuid,
                       user     = user,
                       app_     = app,
                       link     = link )
    act.put()
