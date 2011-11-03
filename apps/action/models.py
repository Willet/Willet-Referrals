#!/usr/bin/env/python

# The Action Model
# A parent class for all User actions 
# ie. ClickAction, VoteAction, ViewAction, etc

__author__    = "Willet, Inc."
__copyright__ = "Copyright 2011, Willet, Inc"

import datetime, logging
import random

from google.appengine.api    import memcache
from google.appengine.api    import datastore_errors 
from google.appengine.ext import deferred
from google.appengine.datastore import entity_pb
from google.appengine.ext    import db
from google.appengine.ext.db import polymodel

from util.consts             import *
from util.helpers            import generate_uuid
from util.model              import Model

"""Helper method to persist actions to datastore"""
def persist_actions(list_keys):
    from apps.sibt.actions import *
    logging.error('persisting list_keys')
    action_dict = memcache.get_multi([key for key in list_keys]) 
    timeout_ms = 100

    for key in list_keys:
        data = action_dict.get(key)
        action = db.model_from_protobuf(entity_pb.EntityProto(data))

        if action:
            while True:
                logging.debug('Model::save(): Trying %s.put, timeout_ms=%i.' % (action.__class__.__name__.lower(), timeout_ms))
                try:
                    another_action = Action.all().filter('uuid =', action.uuid).get()
                    if another_action == None:
                        action.hardPut() # Will validate the instance.
                except datastore_errors.Timeout:
                    thread.sleep(timeout_ms)
                    timeout_ms *= 2
                else:
                    break


## -----------------------------------------------------------------------------
## Action SuperClass -----------------------------------------------------------
## -----------------------------------------------------------------------------
class Action(Model, polymodel.PolyModel):
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
        if 'user' in kwargs:
            if hasattr(kwargs['user'], 'is_admin'):
                if kwargs['user'].is_admin():
                    self.is_admin = True
        super(Action, self).__init__(*args, **kwargs)
    
    def put(self):
        """Override util.model.put with some custom shizzbang"""
        key = self.get_key()
        memcache.set(key, db.model_to_protobuf(self).Encode())

        bucket = random.randint(0, NUM_ACTIONS_MEMCACHE_BUCKETS)
        bucket_key = "_willet_actions_bucket:%s" % bucket
        logging.warn('bucket key: %s' % bucket_key)

        list_identities = memcache.get(bucket_key) or []
        list_identities.append(key)
        memcache.set(bucket_key, list_identities)

        logging.warn('bucket length: %d' % len(list_identities))
        if len(list_identities) > NUM_ACTIONS_MEMCACHE_BUCKETS:
            memcache.set(bucket_key, [])
            logging.warn('bucket overfilling, persisting!')
            deferred.defer(persist_actions, list_identities)

    def get_class_name(self):
        return self.__class__.__name__
    name = property(get_class_name)

    @classmethod
    def _get_from_datastore(cls, uuid):
        """Datastore retrieval using memcache_key"""
        return Action.all().filter('uuid =', uuid).get()

    def validateSelf( self ):
        pass

    def __unicode__(self):
        return self.__str__()

    def __str__(self):
        # Subclasses should override this
        pass
    
    def create( self ):
        if self.user.is_admin():
            self.is_admin = True
            
    ## Accessors 
    @staticmethod
    def count( admins_too = False ):
        if admins_too:
            return Action.all().count()
        else:
            return Action.all().filter( 'is_admin =', False ).count()

    @staticmethod
    def get_all( admins_too = False ):
        if admins_too:
            return Action.all()
        else:
            return Action.all().filter( 'is_admin =', False )

    @staticmethod
    def get_by_uuid( uuid ):
        return Action.get(uuid)

    @staticmethod
    def get_by_user( user ):
        return Action.all().filter( 'user =', user ).get()

    @staticmethod
    def get_by_app( app, admins_too = False ):
        if admins_too:
            return Action.all().filter( 'app_ =', app ).get()
        else:
            return Action.all().filter( 'app_ =', app ).filter('is_admin =', False).get()

    @staticmethod
    def get_by_user_and_app( user, app ):
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
        #self.app_.storeAnalyticsDatum( self.class_name(), self.user, self.link.target_url )
           
    def __str__(self):
        return 'CLICK: %s(%s) %s' % (
                self.user.get_full_name(),
                self.user.uuid,
                self.app_.uuid
        )

## Constructor -----------------------------------------------------------------
"""
# Never call this directly
def create_click_action( user, app, link ):
    # Make the action
    uuid = generate_uuid( 16 )
    act  = ClickAction( key_name = uuid,
                        uuid     = uuid,
                        user     = user,
                        app_     = app,
                        link     = link )
    super(ClickAction, act).create()

    act.put()
"""
   
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
        #self.app_.storeAnalyticsDatum( self.class_name(), self.user, self.link.target_url )
    
    def __str__(self):
        return 'VOTE: %s(%s) %s' % (self.user.get_full_name(), self.user.uuid, self.app_.uuid)

    def validateSelf(self):
        if not (self.vote == 'yes' or self.vote == 'no'):
            raise Exception("Vote type needs to be yes or no")

    @staticmethod
    def get_by_vote(vote):
        return VoteAction.all().filter( 'vote =', vote )

    @staticmethod
    def get_all_yesses():
        return VoteAction.all().filter( 'vote =', 'yes' )

    @staticmethod
    def get_all_nos():
        return VoteAction.all().filter( 'vote =', 'no' )

## Constructor -----------------------------------------------------------------
"""
# Never call this directly
def create_vote_action( user, app, link, vote ):
    # Make the action
    uuid = generate_uuid( 16 )
    act  = VoteAction( key_name = uuid,
                       uuid     = uuid,
                       user     = user,
                       app_     = app,
                       link     = link,
                       vote     = vote )
    super(VoteAction, act).create()

    act.put() 
"""

## -----------------------------------------------------------------------------
## LoadAction Subclass ---------------------------------------------------------------
## -----------------------------------------------------------------------------
class LoadAction( Action ):
    """ Parent class for Load actions.
        ie. ScriptLoad, ButtonLoad """

    url = db.LinkProperty( indexed = True )

    def __str__(self):
        return 'LoadAction: %s(%s) %s' % (self.user.get_full_name(), self.user.uuid, self.app_.uuid)

    @staticmethod
    def get_by_url(url):
        return LoadAction.all().filter('url =', url)

    @staticmethod
    def get_by_user_and_url(user, url):
        return LoadAction.all().filter( 'user = ', user ).filter( 'url =', url )

## Accessors -------------------------------------------------------------------
def get_loads_by_url( url ):
    logging.warn('get_loads_by_url deprecated, use static method LoadAction.get_by_url')
    return LoadAction.all().filter( 'url =', url )

def get_loads_by_user_and_url( user, url ):
    logging.warn('get_loads_by_user_and_url deprecated, use static method LoadAction.get_by_user_and_url')
    return LoadAction.all().filter( 'user = ', user ).filter( 'url =', url )

## -----------------------------------------------------------------------------
## ScriptLoadAction Subclass ---------------------------------------------------------
## -----------------------------------------------------------------------------
class ScriptLoadAction( LoadAction ):
    def __str__(self):
        return 'ScriptLoadAction: %s(%s) %s' % (self.user.get_full_name(), self.user.uuid, self.app_.uuid)

    ## Constructor 
    @staticmethod
    def create( user, app, url ):
        uuid = generate_uuid( 16 )
        act  = ScriptLoadAction( key_name = uuid,
                                 uuid     = uuid,
                                 user     = user,
                                 app_     = app,
                                 url      = url )

        super(ScriptLoadAction, act).create()
        
        act.put()

    @staticmethod
    def get_by_app(app):
        """docstring for get_by_app"""
        return ScriptLoadAction.all().filter( 'app_ =', app )

## Accessors -------------------------------------------------------------------
def get_scriptloads_by_app( app ):
    logging.warn('get_scriptloads_by_app deprecated, use staticmethod')
    return ScriptLoadAction.all().filter( 'app_ =', app )

## -----------------------------------------------------------------------------
## ButtonLoadAction Subclass ---------------------------------------------------
## -----------------------------------------------------------------------------
class ButtonLoadAction( LoadAction ):
    """ Created when a button is loaded.
        ie. "SIBT?" button or Want FB button. """

    def __str__(self):
        return 'ButtonLoadAction: %s(%s) %s' % (self.user.get_full_name(), self.user.uuid, self.app_.uuid)

    ## Constructor 
    @staticmethod
    def create( user, app, url ):
        uuid = generate_uuid( 16 )
        act  = ButtonLoadAction( key_name = uuid,
                                 uuid     = uuid,
                                 user     = user,
                                 app_     = app,
                                 url      = url )
        
        super(ButtonLoadAction, act).create()
        
        act.put()

    @staticmethod
    def get_by_app(app):
        return ButtonLoadAction.all().filter( 'app_ =', app )

    @staticmethod
    def get_by_user_and_url(user, url):
        return ButtonLoadAction.all().filter('user = ', user).filter('url =', url)

## Accessors -------------------------------------------------------------------
def get_buttonloads_by_app( app ):
    logging.warn('get_buttonloads_by_app deprecated')
    return ButtonLoadAction.all().filter( 'app_ =', app )

def get_buttonloads_by_user_and_url( user, url ):
    logging.warn('get_buttonloads_by_user_and_url deprecated')
    return ButtonLoadAction.all().filter('user = ', user).filter('url =', url)

class ShowAction(Action):
    """We are showing something ..."""

    # what we are showing... dumb but true!
    what = db.StringProperty()

    # url/page this was shown on 
    url = db.LinkProperty( indexed = True )
    
    @staticmethod
    def create(user, app, what, url):
        uuid = generate_uuid( 16 )
        action = ShowAction(
                key_name = uuid,
                uuid = uuid,
                user = user,
                app_ = app,
                what = what,
                url = url
        )
        
        super(ShowAction, action).create()
        
        action.put()
        return action

    def __str__(self):
        return 'Showing %s to %s on %s' % (
            self.what,
            self.user.get_first_name(),
            self.url,
        )

class UserAction(Action):
    """A user action, such as clicking on a button or something like that"""

    # what did they do 
    what = db.StringProperty()

    # url/page this was acted on 
    url = db.LinkProperty( indexed = True )
    
    @staticmethod
    def create(user, app, what, url):
        uuid = generate_uuid( 16 )
        action = UserAction(
                key_name = uuid,
                uuid = uuid,
                user = user,
                app_ = app,
                what = what,
                url = url
        )
        
        super(UserAction, action).create()
        
        action.put()
        return action

    def __str__(self):
        return 'User %s did %s on %s' % (
            self.user.get_first_name(),
            self.what,
            self.url,
        )

