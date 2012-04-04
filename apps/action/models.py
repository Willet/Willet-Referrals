#!/usr/bin/env/python

# The Action Model
# A parent class for all User actions 
# ie. ClickAction, VoteAction, ViewAction, etc

__author__ = "Willet, Inc."
__copyright__ = "Copyright 2012, Willet, Inc"

import logging

from google.appengine.api import memcache
from google.appengine.ext import db, deferred
from google.appengine.ext.db import polymodel

from util.consts import *
from util.helpers import generate_uuid
from util.memcache_bucket_config import MemcacheBucketConfig
from util.memcache_ref_prop import MemcacheReferenceProperty
from util.model import Model

"""Helper method to persist actions to datastore"""
def persist_actions(bucket_key, list_keys, decrementing=False):
    pass

## ----------------------------------------------------------------------------
## Action SuperClass ----------------------------------------------------------
## ----------------------------------------------------------------------------
class Action(Model, polymodel.PolyModel):
    """ Whenever a 'User' completes a Willet Action,
        an 'Action' obj will be stored for them.
        This 'Action' class will be subclassed for specific actions
        ie. click, vote, tweet, share, email, etc.
    """
    
    # Datetime when this model was put into the DB
    created = db.DateTimeProperty(auto_now_add=True)
    # Length of time a compound action had persisted prior to its creation
    duration = db.FloatProperty(default = 0.0)
    # Person who did the action
    user = MemcacheReferenceProperty(db.Model, collection_name = 'user_actions')
    # True iff this Action's User is an admin
    is_admin = db.BooleanProperty(default = False)
    # The App that this Action is for
    app_ = db.ReferenceProperty(db.Model, collection_name = 'app_actions')
    
    def __init__(self, *args, **kwargs):
        self._memcache_key = kwargs['uuid'] if 'uuid' in kwargs else None 
        super(Action, self).__init__(*args, **kwargs)
    
    def _validate_self(self):
        if self.duration < 0:
            raise ValueError('duration cannot be less than 0 seconds')

        return True

    def put(self):
        """Override util.model.put with some custom shizzbang"""
        # Not the best spot for this, but I can't think of a better spot either ..
        self.is_admin = self.user.is_admin() 
        
        key = self.get_key()
        memcache.set(key, db.model_to_protobuf(self).Encode(), time=MEMCACHE_TIMEOUT)

        mbc = MemcacheBucketConfig.get_or_create('_willet_actions_bucket')
        bucket = mbc.get_random_bucket()
        # logging.info('bucket: %s' % bucket)

        list_identities = memcache.get(bucket) or []
        list_identities.append(key)

        # logging.info('bucket length: %d/%d' % (len(list_identities), mbc.count))
        if len(list_identities) > mbc.count:
            memcache.set(bucket, [], time=MEMCACHE_TIMEOUT)
            logging.warn('bucket overflowing, persisting!')
            deferred.defer(persist_actions, bucket, list_identities, _queue='slow-deferred')
        else:
            memcache.set(bucket, list_identities, time=MEMCACHE_TIMEOUT)

    def get_class_name(self):
        return self.__class__.__name__
    name = property(get_class_name)

    @classmethod
    def _get_from_datastore(cls, uuid):
        """Datastore retrieval using memcache_key"""
        return Action.all().filter('uuid =', uuid).get()

    def _validate_self(self):
        return True

    def __unicode__(self):
        return self.__str__()

    def __str__(self):
        # Subclasses should override this
        pass
    
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
    def get_by_app(app, admins_too = False):
        app_actions = Action.all().filter('app_ =', app)
        if admins_too:
            return app_actions.get()
        else:
            return app_actions.filter('is_admin =', False).get()

    @staticmethod
    def get_by_user_and_app(user, app):
        return Action.all().filter('user =', user).filter('app_ =', app).get()


## -----------------------------------------------------------------------------
## ClickAction Subclass --------------------------------------------------------
## -----------------------------------------------------------------------------
class ClickAction(Action):
    """ Designates a 'click' action for a User. 
        Currently used for 'SIBT' and 'WOSIB' Apps
    """
    
    # Link that caused the click action ...
    link = db.ReferenceProperty(db.Model, collection_name = "link_clicks")
    
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

    def _validate_self(self):
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


## -----------------------------------------------------------------------------
## LoadAction Subclass ---------------------------------------------------------------
## -----------------------------------------------------------------------------
class LoadAction( Action ):
    """ Parent class for Load actions.
        ie. ScriptLoad, ButtonLoad """

    url = db.LinkProperty(indexed = True, default=True)

    def __str__(self):
        return 'LoadAction: %s(%s) %s' % (self.user.get_full_name(), self.user.uuid, self.app_.uuid)

    @staticmethod
    def get_by_url(url):
        return LoadAction.all().filter('url =', url)

    @staticmethod
    def get_by_user_and_url(user, url):
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
        act = ScriptLoadAction( key_name = uuid,
                                 uuid = uuid,
                                 user = user,
                                 app_ = app,
                                 url = url )

        act.put()

    @staticmethod
    def get_by_app(app):
        """docstring for get_by_app"""
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
        act = ButtonLoadAction( key_name = uuid,
                                 uuid = uuid,
                                 user = user,
                                 app_ = app,
                                 url = url )
        
        act.put()

    @staticmethod
    def get_by_app(app):
        return ButtonLoadAction.all().filter( 'app_ =', app )

    @staticmethod
    def get_by_user_and_url(user, url):
        return ButtonLoadAction.all().filter('user = ', user).filter('url =', url)

## -----------------------------------------------------------------------------
## ShowAction Subclass ---------------------------------------------------
## -----------------------------------------------------------------------------
class ShowAction(Action):
    """We are showing something ..."""

    # what we are showing... dumb but true!
    what = db.StringProperty()

    # url/page this was shown on 
    url = db.LinkProperty(indexed = True)
    
    @staticmethod
    def create(user, app, what, url):
        uuid = generate_uuid(16)
        action = ShowAction(
            key_name=uuid,
            uuid=uuid,
            user=user,
            app_=app,
            what=what,
            url=url
        )
        
        action.put()
        return action

    def __str__(self):
        return 'Showing %s to %s on %s' % (
            self.what,
            self.user.get_first_name(),
            self.url,
        )

## -----------------------------------------------------------------------------
## UserAction Subclass ---------------------------------------------------
## -----------------------------------------------------------------------------
class UserAction(Action):
    """A user action, such as clicking on a button or something like that"""

    # what did they do 
    what = db.StringProperty()

    # url/page this was acted on 
    url = db.LinkProperty(indexed = True)
    
    @staticmethod
    def create(user, app, what, url):
        uuid = generate_uuid(16)
        action = UserAction(
            key_name=uuid,
            uuid=uuid,
            user=user,
            app_=app,
            what=what,
            url=url
        )
        
        action.put()
        return action

    def __str__(self):
        return 'User %s did %s on %s' % (
            self.user.get_first_name(),
            self.what,
            self.url,
        )
