#!/usr/bin/env/python

# Actions for SIBT
# SIBTClickAction, 
__author__    = "Willet, Inc."
__copyright__ = "Copyright 2011, Willet, Inc"

import datetime
import logging

from google.appengine.api   import memcache
from google.appengine.ext   import db
from google.appengine.datastore import entity_pb

from apps.action.models     import ClickAction
from apps.action.models     import VoteAction
from apps.action.models     import ShowAction 
from apps.action.models     import UserAction 

from apps.sibt.models import SIBTInstance

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
        action = SIBTClickAction(
                key_name = uuid,
                uuid = uuid,
                user = user,
                app_ = app,
                link = link,
                url = link.target_url,
                sibt_instance = link.sibt_instance.get()
        )
        #super(SIBTClickAction, act).create()

        action.put()

        tracking_keys = memcache.get(action.get_tracking_key()) or []
        tracking_keys.append(action.get_key())
        memcache.set(action.get_tracking_key(), tracking_keys)
        
        return action 

    ## Accessors 
    @staticmethod
    def get_for_instance(app, user, url):
        tracking = SIBTClickAction.get_tracking_by_user_and_app(user, app)
        actions = memcache.get_multi(tracking)
        instances = SIBTInstance.all(key_only=True)\
            .filter('url =', url)\
            .filter('is_live =', True)\
            .fetch(100)
        key_list = [instance.key() for instance in instances]
        for key in tracking:
            model = db.model_from_protobuf(entity_pb.EntityProto(actions.get(key)))
            if model.sibt_instance.key() in key_list:
                return model

        return SIBTClickAction.all()\
                .filter('user =', user)\
                .filter('url =', url)\
                .filter('sibt_instance IN', key_list)\
                .get()

    @staticmethod
    def get_by_instance(instance):
        return SIBTClickAction.all().filter('sibt_instance =', instance)

    @classmethod
    def get_tracking_by_user_and_app(cls, user, app):
        tracking_key = '%s-%s-%s' % (
            cls.__name__,
            app.uuid,
            user.uuid
        )
        return memcache.get(tracking_key) or []
    
    def get_tracking_key(self):
        return '%s-%s-%s' % (
            self.__class__.__name__,
            self.app_.uuid,
            self.user.uuid
        )

## -----------------------------------------------------------------------------
## SIBTVoteAction Subclass ----------------------------------------------------
## -----------------------------------------------------------------------------
class SIBTVoteAction(VoteAction):
    """ Designates a 'vote' action for a User on a SIBT instance. 
        Currently used for 'SIBT' App """

    sibt_instance = db.ReferenceProperty( db.Model, collection_name="vote_actions" )

    # URL that was voted on
    url           = db.LinkProperty( indexed = True )

    ## Constructor
    @staticmethod
    def create(user, instance, vote):
        # Make the action
        uuid = generate_uuid( 16 )
        action = SIBTVoteAction(  key_name = uuid,
                                uuid     = uuid,
                                user     = user,
                                app_     = instance.app_,
                                link     = instance.link,
                                url      = instance.link.target_url,
                                sibt_instance = instance,
                                vote     = vote )
        #super(SIBTVoteAction, act).create()
        action.put()
        
        # we memcache by classname-instance_uuid-user_uuid
        # so we can look it up really easily later on
        memcache.set(action.get_tracking_key(), action.get_key())

        return action
    
    def __str__(self):
        return 'SIBTVOTE: %s(%s) %s' % (self.user.get_full_name(), self.user.uuid, self.app_.uuid)

    @classmethod
    def get_tracking_by_user_and_instance(cls, user, sibt_instance):
        tracking_key = '%s-%s-%s' % (
            cls.__name__,
            sibt_instance.uuid,
            user.uuid
        )
        return memcache.get(tracking_key) or None 
    
    def get_tracking_key(self):
        return '%s-%s-%s' % (
            self.__class__.__name__,
            self.sibt_instance.uuid,
            self.user.uuid
        )

    ## Accessors 
    @staticmethod
    def get_by_instance( instance ):
        return SIBTVoteAction.all().filter( 'sibt_instance =', instance )

    @staticmethod
    def get_by_app_and_instance_and_user( a, i, u ):
        key = SIBTVoteAction.get_tracking_by_user_and_instance(u, i)
        if key:
            action = SIBTVoteAction.get(key)
            if action:
                return action

        return SIBTVoteAction.all().filter('app_ =', a)\
                                   .filter('sibt_instance =', i)\
                                   .filter('user =', u)\
                                   .get()

    @staticmethod
    def get_by_app_and_instance( a, i ):
        return SIBTVoteAction.all().filter('app_ =', a)\
                                   .filter('sibt_instance =', i).get()

class SIBTShowAction(ShowAction):
    sibt_instance = db.ReferenceProperty( db.Model, collection_name="show_actions" )

    ## Constructor
    @staticmethod
    def create(user, instance, what):
        # Make the action
        uuid = generate_uuid( 16 )
        act  = SIBTShowAction(  key_name = uuid,
                                uuid     = uuid,
                                user     = user,
                                app_     = instance.app_,
                                link     = instance.link,
                                url      = instance.link.target_url,
                                what = what,
                                sibt_instance = instance)
        #super(SIBTShowAction, act).create()
        act.put()
        return act
    
    def __str__(self):
        return 'Showing %s to %s(%s) for sibt instance %s on site %s' % (
                self.what,
                self.user.get_full_name(), 
                self.user.uuid,
                self.sibt_instance.uuid,
                self.sibt_instance.app_.client.domain
        )

    ## Accessors 
    @staticmethod
    def get_by_instance( instance ):
        return SIBTShowAction.all().filter('sibt_instance =', instance)

    @staticmethod
    def get_by_app_and_instance_and_user(app, instance, user):
        return SIBTVoteAction.all().filter('app_ =', app)\
                                   .filter('sibt_instance =', instance)\
                                   .filter('user =', user)\
                                   .get()

    @staticmethod
    def get_by_app_and_instance(app, instance):
        return SIBTVoteAction.all().filter('app_ =', app)\
                                   .filter('sibt_instance =', instance).get()

class SIBTShowingButton(ShowAction):
    @staticmethod
    def create(user, **kwargs):
        app = None
        url = None
        try:
            app = kwargs['app']
            url = kwargs['url']
        except Exception, e:
            logging.error('invalid parameters: %s' % e, exc_info=True)

        what = 'SIBTShowingButton'
        uuid = generate_uuid( 16 )
        action = SIBTShowingButton(
                key_name = uuid,
                uuid = uuid,
                user = user,
                app_ = app,
                what = what,
                url = url
        )
        action.put()

        # tracking urls for fast lookup
        tracking_urls = memcache.get(action.get_tracking_key()) or []
        tracking_urls.append(url)
        memcache.set(action.get_tracking_key(), tracking_urls)
        return action

    @classmethod
    def get_tracking_by_user_and_app(cls, user, app):
        tracking_key = '%s-%s-%s' % (
            cls.__name__,
            app.uuid,
            user.uuid
        )
        return memcache.get(tracking_key) or []
    
    def get_tracking_key(self):
        return '%s-%s-%s' % (
            self.__class__.__name__,
            self.app_.uuid,
            self.user.uuid
        )

class SIBTShowingResults(SIBTShowAction):
    @staticmethod
    def create(user, **kwargs):
        what = 'SIBTResults'
        uuid = generate_uuid(16)

        # make sure we get an instance
        instance = None
        try:
            instance = kwargs['instance']
        except Exception, e:
            logging.error('error getting instance: %s' % e, exc_info=True)

        action = SIBTShowingResults(
                key_name = uuid,
                uuid     = uuid,
                user     = user,
                app_     = instance.app_,
                link     = instance.link,
                url      = instance.link.target_url,
                what = what,
                sibt_instance = instance
        )
        #super(SIBTShowingResults, action).create()
        action.put()
        return action

class SIBTShowingResultsToAsker(SIBTShowAction):
    @staticmethod
    def create(user, **kwargs):
        what = 'SIBTResultsToAsker'
        uuid = generate_uuid(16)

        # make sure we get an instance
        instance = None
        try:
            instance = kwargs['instance']
        except Exception, e:
            logging.error('error getting instance: %s' % e, exc_info=True)

        action = SIBTShowingResultsToAsker(
                key_name = uuid,
                uuid     = uuid,
                user     = user,
                app_     = instance.app_,
                link     = instance.link,
                url      = instance.link.target_url,
                what = what,
                sibt_instance = instance
        )
        #super(SIBTShowingResultsToAsker, action).create()
        action.put()
        return action

class SIBTShowingVote(SIBTShowAction):
    @staticmethod
    def create(user, **kwargs):
        what = 'SIBTVote'
        uuid = generate_uuid(16)

        # make sure we get an instance
        instance = None
        try:
            instance = kwargs['instance']
        except Exception, e:
            logging.error('error getting instance: %s' % e, exc_info=True)
        
        action = SIBTShowingVote(
                key_name = uuid,
                uuid     = uuid,
                user     = user,
                app_     = instance.app_,
                link     = instance.link,
                url      = instance.link.target_url,
                what = what,
                sibt_instance = instance
        )
        #super(SIBTShowingVote, action).create()
        action.put()
        return action

class SIBTInstanceAction(UserAction):
    sibt_instance = db.ReferenceProperty(db.Model, collection_name="inst_actions")

    ## Constructor
    @staticmethod
    def create(user, instance, what):
        # Make the action
        uuid = generate_uuid( 16 )
        action = SIBTVoteAction(
                key_name = uuid,
                uuid     = uuid,
                user     = user,
                app_     = instance.app_,
                link     = instance.link,
                url      = instance.link.target_url,
                sibt_instance = instance,
                what = what
        )
        #super(SIBTVoteAction, action).create()
        action.put()

        return action
    
    def __str__(self):
        return 'SIBTInstanceAction: User %s did %s on %s' % (
                self.user.get_full_name(), 
                self.what,
                self.app_.client.domain
        )

class SIBTInstanceCreated(SIBTInstanceAction):
    @staticmethod
    def create(user, **kwargs):
        what = 'SIBTInstanceCreated'
        medium = None
    
        # make sure we get an instance
        instance = None
        try:
            instance = kwargs['instance']
            medium = kwargs['medium']
        except Exception, e:
            logging.error('error getting instance: %s' % e, exc_info=True)
        
        uuid = generate_uuid(16)
        action = SIBTInstanceCreated(
                key_name = uuid,
                uuid     = uuid,
                user     = user,
                app_     = instance.app_,
                link     = instance.link,
                url      = instance.link.target_url,
                what = what,
                sibt_instance = instance
        )
        #super(SIBTInstanceCreated, action).create()
        action.put()
        return action

##
## SIBT Show event with NO INSTANCE
##
class SIBTShowingAskIframe(ShowAction):
    @staticmethod
    def create(user, **kwargs):
        what = 'SIBTAskIframe'
        uuid = generate_uuid(16)

        # make sure we get an instance
        url = None
        app = None
        try:
            url = kwargs['url']
            app = kwargs['app']
        except Exception, e:
            logging.error('error getting url: %s' % e, exc_info=True)
        
        action = SIBTShowingAskIframe(
                key_name = uuid,
                uuid = uuid,
                user = user,
                url = url,
                app_ = app,
                what = what
        )
        #super(SIBTShowingAskIframe, action).create()
        action.put()
        return action

class SIBTShowingTopBarAsk(ShowAction):
    @staticmethod
    def create(user, **kwargs):
        what = 'SIBTTopBarAsk'
        uuid = generate_uuid(16)

        # make sure we get an instance
        url = None
        app = None
        try:
            url = kwargs['url']
            app = kwargs['app']
        except Exception, e:
            logging.error('error getting url: %s' % e, exc_info=True)
        
        action = SIBTShowingTopBarAsk(
                key_name = uuid,
                uuid = uuid,
                user = user,
                url = url,
                app_ = app,
                what = what
        )
        #super(SIBTShowingAskIframe, action).create()
        action.put()
        return action
        
class SIBTShowingAskTopBarIframe(ShowAction):
    @staticmethod
    def create(user, **kwargs):
        what = 'SIBTAskTopBarIframe'
        uuid = generate_uuid(16)

        # make sure we get an instance
        url = None
        app = None
        try:
            url = kwargs['url']
            app = kwargs['app']
        except Exception, e:
            logging.error('error getting url: %s' % e, exc_info=True)
        
        action = SIBTShowingAskTopBarIframe(
                key_name = uuid,
                uuid = uuid,
                user = user,
                url = url,
                app_ = app,
                what = what
        )
        #super(SIBTShowingAskTopBarIframe, action).create()
        action.put()
        return action

class SIBTUserClickedTopBarAsk(UserAction):
    @staticmethod
    def create(user, **kwargs):
        # Make the action
        what = 'SIBTUserClickedTopBarAsk'
        url = None
        app = None
        try:
            app = kwargs['app']
            url = kwargs['url']
        except Exception,e:
            logging.error(e, exc_info=True)

        uuid = generate_uuid( 16 )
        action = SIBTUserClickedTopBarAsk(
                key_name = uuid,
                uuid     = uuid,
                user     = user,
                app_     = app,
                url      = url,
                what = what
        )
        action.put()

        return action

class SIBTUserClickedButtonAsk(UserAction):
    @staticmethod
    def create(user, **kwargs):
        # Make the action
        what = 'SIBTUserClickedButtonAsk'
        url = None
        app = None
        try:
            app = kwargs['app']
            url = kwargs['url']
        except Exception,e:
            logging.error(e, exc_info=True)

        uuid = generate_uuid( 16 )
        action = SIBTUserClickedButtonAsk(
                key_name = uuid,
                uuid     = uuid,
                user     = user,
                app_     = app,
                url      = url,
                what = what
        )
        action.put()

        return action
    
class SIBTUserClosedTopBar(UserAction):
    @staticmethod
    def create(user, **kwargs):
        # Make the action
        what = 'SIBTUserClosedTopBar'
        url = None
        app = None
        try:
            app = kwargs['app']
            url = kwargs['url']
        except Exception,e:
            logging.error(e, exc_info=True)

        uuid = generate_uuid( 16 )
        action = SIBTUserClosedTopBar(
                key_name = uuid,
                uuid     = uuid,
                user     = user,
                app_     = app,
                url      = url,
                what = what
        )
        action.put()
        return action

class SIBTAskUserClickedEditMotivation(UserAction):
    @staticmethod
    def create(user, **kwargs):
        # Make the action
        what = 'SIBTAskUserClickedEditMotivation'
        url = None
        app = None
        try:
            app = kwargs['app']
            url = kwargs['url']
        except Exception,e:
            logging.error(e, exc_info=True)

        uuid = generate_uuid( 16 )
        action = SIBTAskUserClickedEditMotivation(
                key_name = uuid,
                uuid     = uuid,
                user     = user,
                app_     = app,
                url      = url,
                what = what
        )
        action.put()
        return action

class SIBTAskUserClosedIframe(UserAction):
    @staticmethod
    def create(user, **kwargs):
        # Make the action
        what = 'SIBTAskUserClosedIframe'
        url = None
        app = None
        try:
            app = kwargs['app']
            url = kwargs['url']
        except Exception,e:
            logging.error(e, exc_info=True)

        uuid = generate_uuid( 16 )
        action = SIBTAskUserClosedIframe(
                key_name = uuid,
                uuid     = uuid,
                user     = user,
                app_     = app,
                url      = url,
                what = what
        )
        action.put()
        return action

class SIBTAskUserClickedShare(UserAction):
    @staticmethod
    def create(user, **kwargs):
        # Make the action
        what = 'SIBTAskUserClickedShare'
        url = None
        app = None
        try:
            app = kwargs['app']
            url = kwargs['url']
        except Exception,e:
            logging.error(e, exc_info=True)

        uuid = generate_uuid( 16 )
        action = SIBTAskUserClickedShare(
                key_name = uuid,
                uuid     = uuid,
                user     = user,
                app_     = app,
                url      = url,
                what = what
        )
        action.put()
        return action

class SIBTUserAction(UserAction):
    sibt_instance = db.ReferenceProperty( db.Model, collection_name="sibt_user_actions" )

    ## Constructor
    @staticmethod
    def create(user, instance, what):
        # Make the action
        uuid = generate_uuid( 16 )
        act  = SIBTUserAction(  key_name = uuid,
                                uuid     = uuid,
                                user     = user,
                                app_     = instance.app_,
                                link     = instance.link,
                                url      = instance.link.target_url,
                                what = what,
                                sibt_instance = instance)
        #super(SIBTShowAction, act).create()
        act.put()
        return act
    
    def __str__(self):
        return '%s(%s) did %s to %s(%s) for sibt instance %s on site %s' % (
                self.user.get_full_name(), 
                self.user.uuid,
                self.what,
                self.sibt_instance.uuid,
                self.sibt_instance.app_.client.domain
        )

    ## Accessors 
    @staticmethod
    def get_by_instance(instance):
        return SIBTUserAction.all().filter('sibt_instance =', instance)

    @staticmethod
    def get_by_app_and_instance_and_user(app, instance, user):
        return SIBTUserAction.all().filter('app_ =', app)\
                                   .filter('sibt_instance =', instance)\
                                   .filter('user =', user)\
                                   .get()

    @staticmethod
    def get_by_app_and_instance(app, instance):
        return SIBTUserAction.all().filter('app_ =', app)\
                                   .filter('sibt_instance =', instance).get()


