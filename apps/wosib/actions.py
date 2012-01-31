#!/usr/bin/env/python

__author__    = "Willet, Inc."
__copyright__ = "Copyright 2012, Willet, Inc"

import datetime
import logging

from google.appengine.api   import memcache
from google.appengine.ext   import db
from google.appengine.datastore import entity_pb

from apps.action.models     import Action
from apps.action.models     import ClickAction
from apps.action.models     import ShowAction
from apps.action.models     import UserAction
from apps.action.models     import VoteAction

from apps.gae_bingo.gae_bingo import bingo

from util.helpers           import generate_uuid
from util.consts import MEMCACHE_TIMEOUT

## -----------------------------------------------------------------------------
## WOSIBClickAction Subclass ----------------------------------------------------
## -----------------------------------------------------------------------------
class WOSIBClickAction(ClickAction):
    """ Designates a 'click' action for a User on a WOSIB instance. """

    wosib_instance = db.ReferenceProperty(db.Model, collection_name="wosib_click_actions")

    # URL that was clicked on
    url = db.LinkProperty(indexed = True)

    def __str__(self):
        return 'WOSIBCLICK: %s(%s) %s' % (self.user.get_full_name(), self.user.uuid, self.app_.uuid)

    ## Constructor 
    @staticmethod
    def create( user, app, link ):
        # Make the action
        uuid = generate_uuid( 16 )
        action = WOSIBClickAction(
                key_name = uuid,
                uuid = uuid,
                user = user,
                app_ = app,
                link = link,
                url = link.target_url,
                wosib_instance = link.wosib_instance.get()
        )

        action.put()

        tracking_keys = memcache.get(action.get_tracking_key()) or []
        tracking_keys.append(action.get_key())
        memcache.set(action.get_tracking_key(), tracking_keys, time=MEMCACHE_TIMEOUT)
        
        return action 

    ## Accessors 
    @staticmethod
    def get_for_instance(app, user, url, key_list):
        logging.debug('getting action for:\napp: %s\nuser: %s\nurl: %s\nkeys: %s' % (
            app, user, url, key_list    
        ))
        model = None
        try:
            tracking = WOSIBClickAction.get_tracking_by_user_and_app(user, app)
            actions = memcache.get_multi(tracking)
            
            for key in tracking:
                model = db.model_from_protobuf(entity_pb.EntityProto(actions.get(key)))
                logging.info('got tracking key: %s and model %s %s' % (
                    key, 
                    model,
                    model.wosib_instance.key().id_or_name()
                ))
                if model.wosib_instance.key().id_or_name() in key_list:
                    break
                model = None
            if not model:
                model = WOSIBClickAction.all()\
                    .filter('user =', user)\
                    .filter('url =', url)\
                    .filter('wosib_instance IN', key_list)\
                    .get()
        except Exception, e:
            logging.error('could not get model for instance: %s' % e, exc_info=True)
        return model

    @staticmethod
    def get_by_instance(instance):
        return WOSIBClickAction.all().filter('wosib_instance =', instance)

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
## WOSIBVoteAction Subclass ----------------------------------------------------
## -----------------------------------------------------------------------------
class WOSIBVoteAction(VoteAction):
    """ Designates a 'vote' action for a User on a WOSIB instance. 
        Currently used for 'WOSIB' App """

    wosib_instance = db.ReferenceProperty( db.Model, collection_name="wosib_vote_actions" )
    
    # because WOSIB contains more than one product, we have to record which
    # product to which this vote corresponds
    product_uuid = db.StringProperty(indexed=True, required=True)
    
    # URL that was voted on
    url           = db.LinkProperty( indexed = True )

    ## Constructor
    @staticmethod
    def create(user, instance, vote, product):
        # Make the action
        uuid = generate_uuid( 16 )
        action = WOSIBVoteAction(  key_name = uuid,
                                uuid     = uuid,
                                user     = user,
                                app_     = instance.app_,
                                link     = instance.link,
                                url      = instance.link.target_url,
                                product_uuid = product,
                                wosib_instance = instance,
                                vote     = vote )
        #super(WOSIBVoteAction, act).create()
        action.put()
        
        # we memcache by classname-instance_uuid-user_uuid
        # so we can look it up really easily later on
        memcache.set(action.get_tracking_key(), action.get_key(), time=MEMCACHE_TIMEOUT)

        return action
    
    def __str__(self):
        return 'WOSIBVOTE: %s(%s) %s' % (self.user.get_full_name(), self.user.uuid, self.app_.uuid)

    @classmethod
    def get_tracking_by_user_and_instance(cls, user, wosib_instance):
        tracking_key = '%s-%s-%s' % (
            cls.__name__,
            wosib_instance.uuid,
            user.uuid
        )
        return memcache.get(tracking_key) or None 
    
    def get_tracking_key(self):
        return '%s-%s-%s' % (
            self.__class__.__name__,
            self.wosib_instance.uuid,
            self.user.uuid
        )

    ## Accessors 
    @staticmethod
    def get_by_instance( instance ):
        return WOSIBVoteAction.all().filter( 'wosib_instance =', instance )

    @staticmethod
    def get_by_app_and_instance_and_user(a, i, u):
        action = None
        key = WOSIBVoteAction.get_tracking_by_user_and_instance(u, i)
        if key:
            action = WOSIBVoteAction.get(key)

        if not action:
            action = WOSIBVoteAction.all()\
                    .filter('app_ =', a)\
                    .filter('wosib_instance =', i)\
                    .filter('user =', u)\
                    .get()
        return action

    @staticmethod
    def get_by_app_and_instance( a, i ):
        return WOSIBVoteAction.all()\
                .filter('app_ =', a)\
                .filter('wosib_instance =', i)\
                .get()

class WOSIBShowAction(ShowAction):
    ''' Class for storing WOSIB actions - whenever a UI component is shown or hidden. 
        If a user is detected, the WOSIBUserAction class is recommended instead. '''
    wosib_instance = db.ReferenceProperty( db.Model, collection_name="wosib_show_actions" )

    ## Constructor
    @staticmethod
    def create(user, instance, what):
        # Make the action
        uuid = generate_uuid( 16 )
        act  = WOSIBShowAction(  key_name = uuid,
                                uuid     = uuid,
                                user     = user,
                                app_     = instance.app_,
                                link     = instance.link,
                                url      = instance.link.target_url,
                                what = what,
                                wosib_instance = instance)
        act.put()
        return act
    
    def __str__(self):
        return 'Showing %s to %s(%s) for wosib instance %s on site %s' % (
                self.what,
                self.user.get_full_name(), 
                self.user.uuid,
                self.wosib_instance.uuid,
                self.wosib_instance.app_.client.domain
        )

    ## Accessors 
    @staticmethod
    def get_by_instance( instance ):
        return WOSIBShowAction.all().filter('wosib_instance =', instance)

    @staticmethod
    def get_by_app_and_instance_and_user(app, instance, user):
        return WOSIBVoteAction.all().filter('app_ =', app)\
                                   .filter('wosib_instance =', instance)\
                                   .filter('user =', user)\
                                   .get()

    @staticmethod
    def get_by_app_and_instance(app, instance):
        return WOSIBVoteAction.all().filter('app_ =', app)\
                                   .filter('wosib_instance =', instance).get()

class WOSIBShowingButton(WOSIBShowAction):
    #TODO: check what this is all about
    @staticmethod
    def create(user, **kwargs):
        app = None
        url = None
        try:
            app = kwargs['app']
            url = kwargs['url']
        except Exception, e:
            logging.error('invalid parameters: %s' % e, exc_info=True)

        what = 'WOSIBShowingButton'
        uuid = generate_uuid( 16 )
        action = WOSIBShowingButton(
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
        memcache.set(action.get_tracking_key(), tracking_urls, time=MEMCACHE_TIMEOUT)
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

class WOSIBShowingResults(WOSIBShowAction):
    @staticmethod
    def create(user, **kwargs):
        what = 'WOSIBResults'
        uuid = generate_uuid(16)

        # make sure we get an instance
        instance = None
        try:
            instance = kwargs['instance']
        except Exception, e:
            logging.error('error getting instance: %s' % e, exc_info=True)

        action = WOSIBShowingResults(
                key_name = uuid,
                uuid     = uuid,
                user     = user,
                app_     = instance.app_,
                link     = instance.link,
                url      = instance.link.target_url,
                what = what,
                wosib_instance = instance
        )
        #super(WOSIBShowingResults, action).create()
        action.put()
        return action

class WOSIBShowingResultsToAsker(WOSIBShowAction):
    @staticmethod
    def create(user, **kwargs):
        what = 'WOSIBResultsToAsker'
        uuid = generate_uuid(16)

        # make sure we get an instance
        instance = None
        try:
            instance = kwargs['instance']
        except Exception, e:
            logging.error('error getting instance: %s' % e, exc_info=True)

        action = WOSIBShowingResultsToAsker(
                key_name = uuid,
                uuid     = uuid,
                user     = user,
                app_     = instance.app_,
                link     = instance.link,
                url      = instance.link.target_url,
                what = what,
                wosib_instance = instance
        )
        #super(WOSIBShowingResultsToAsker, action).create()
        action.put()
        return action

class WOSIBShowingVote(WOSIBShowAction):
    @staticmethod
    def create(user, **kwargs):
        what = 'WOSIBVote'
        uuid = generate_uuid(16)

        # make sure we get an instance
        instance = None
        try:
            instance = kwargs['instance']
        except Exception, e:
            logging.error('error getting instance: %s' % e, exc_info=True)
        
        action = WOSIBShowingVote(
                key_name = uuid,
                uuid     = uuid,
                user     = user,
                app_     = instance.app_,
                link     = instance.link,
                url      = instance.link.target_url,
                what = what,
                wosib_instance = instance
        )
        #super(WOSIBShowingVote, action).create()
        action.put()
        return action

class WOSIBInstanceAction(UserAction):
    wosib_instance = db.ReferenceProperty(db.Model, collection_name="wosib_inst_actions")

    ## Constructor
    @staticmethod
    def create(user, instance, what):
        # Make the action
        uuid = generate_uuid( 16 )
        action = WOSIBVoteAction(
                key_name = uuid,
                uuid     = uuid,
                user     = user,
                app_     = instance.app_,
                link     = instance.link,
                url      = instance.link.target_url,
                wosib_instance = instance,
                what = what
        )
        #super(WOSIBVoteAction, action).create()
        action.put()

        return action
    
    def __str__(self):
        return 'WOSIBInstanceAction: User %s did %s on %s' % (
                self.user.get_full_name(), 
                self.what,
                self.app_.client.domain
        )

class WOSIBVisitLength(UserAction):
    '''action recording the length of visits (if onbeforeunload is called).'''
    @staticmethod
    def create(user, **kwargs):
        # Make the action
        what = 'WOSIBVisitLength'
        url = None
        app = None
        duration= 0.0
        try:
            logging.debug ('kwargs for WOSIBVisitLength: %s' % kwargs)
            app = kwargs['app']
            url = kwargs['url']
            duration = float (kwargs['duration'])
        except Exception,e:
            logging.error(e, exc_info=True)

        uuid = generate_uuid( 16 )
        action = WOSIBVisitLength(
                key_name = uuid,
                uuid     = uuid,
                user     = user,
                app_     = app,
                url      = url,
                what     = what,
                duration = duration
        )
        action.put()

        return action

class WOSIBInstanceCreated(WOSIBInstanceAction):
    medium = db.StringProperty( default="", indexed=True )

    @staticmethod
    def create(user, **kwargs):
        what = 'WOSIBInstanceCreated'
        medium = ""
    
        # make sure we get an instance
        instance = None
        try:
            instance = kwargs['instance']
            medium = kwargs['medium']
        except Exception, e:
            logging.error('error getting instance: %s' % e, exc_info=True)
        
        uuid = generate_uuid(16)
        action = WOSIBInstanceCreated(
                key_name = uuid,
                uuid     = uuid,
                user     = user,
                app_     = instance.app_,
                link     = instance.link,
                url      = instance.link.target_url,
                what     = what,
                medium   = medium,
                wosib_instance = instance
        )
        #super(WOSIBInstanceCreated, action).create()
        action.put()
        return action

##
## WOSIB Show event with NO INSTANCE
##
class WOSIBShowingAskIframe(ShowAction):
    @staticmethod
    def create(user, **kwargs):
        what = 'WOSIBAskIframe'
        uuid = generate_uuid(16)

        # make sure we get an instance
        url = None
        app = None
        try:
            url = kwargs['url']
            app = kwargs['app']
        except Exception, e:
            logging.error('error getting url: %s' % e, exc_info=True)
        
        action = WOSIBShowingAskIframe(
                key_name = uuid,
                uuid = uuid,
                user = user,
                url = url,
                app_ = app,
                what = what
        )
        #super(WOSIBShowingAskIframe, action).create()
        action.put()
        return action

class WOSIBAskIframeCancelled(ShowAction):
    """ Cancelled immediately after opening - ie. no other actions in between open and close.
        Closed using "cancel' button on splash screen """
    @staticmethod
    def create(user, **kwargs):
        what = 'WOSIBAskIframeCancelled'
        uuid = generate_uuid(16)

        # make sure we get an instance
        url = None
        app = None
        try:
            url = kwargs['url']
            app = kwargs['app']
        except Exception, e:
            logging.error('error getting url: %s' % e, exc_info=True)
        
        action = WOSIBAskIframeCancelled(
                key_name = uuid,
                uuid = uuid,
                user = user,
                url = url,
                app_ = app,
                what = what
        )
        #super(WOSIBShowingAskIframe, action).create()
        action.put()
        return action

class WOSIBOverlayCancelled(ShowAction):
    """ Cancelled / closed iframe by clicking on the overlay (ie. outside of iframe) """
    @staticmethod
    def create(user, **kwargs):
        what = 'WOSIBOverlayCancelled'
        uuid = generate_uuid(16)

        # make sure we get an instance
        url = None
        app = None
        try:
            url = kwargs['url']
            app = kwargs['app']
        except Exception, e:
            logging.error('error getting url: %s' % e, exc_info=True)
        
        action = WOSIBOverlayCancelled(
                key_name = uuid,
                uuid = uuid,
                user = user,
                url = url,
                app_ = app,
                what = what
        )
        action.put()
        return action

class WOSIBUserClickedButtonAsk(UserAction):
    @staticmethod
    def create(user, **kwargs):
        # Make the action
        what = 'WOSIBUserClickedButtonAsk'
        url = None
        app = None
        try:
            app = kwargs['app']
            url = kwargs['url']
        except Exception,e:
            logging.error(e, exc_info=True)

        uuid = generate_uuid( 16 )
        action = WOSIBUserClickedButtonAsk(
                key_name = uuid,
                uuid     = uuid,
                user     = user,
                app_     = app,
                url      = url,
                what = what
        )
        action.put()

        return action

class WOSIBAskUserClickedEditMotivation(UserAction):
    @staticmethod
    def create(user, **kwargs):
        # Make the action
        what = 'WOSIBAskUserClickedEditMotivation'
        url = None
        app = None
        try:
            app = kwargs['app']
            url = kwargs['url']
        except Exception,e:
            logging.error(e, exc_info=True)

        uuid = generate_uuid( 16 )
        action = WOSIBAskUserClickedEditMotivation(
                key_name = uuid,
                uuid     = uuid,
                user     = user,
                app_     = app,
                url      = url,
                what = what
        )
        action.put()
        return action

class WOSIBAskUserClickedShare(UserAction):
    @staticmethod
    def create(user, **kwargs):
        # Make the action
        what = 'WOSIBAskUserClickedShare'
        url = None
        app = None
        try:
            app = kwargs['app']
            url = kwargs['url']
        except Exception,e:
            logging.error(e, exc_info=True)

        uuid = generate_uuid( 16 )
        action = WOSIBAskUserClickedShare(
                key_name = uuid,
                uuid     = uuid,
                user     = user,
                app_     = app,
                url      = url,
                what = what
        )
        action.put()
        return action

class WOSIBConnectFBCancelled(UserAction):
    @staticmethod
    def create(user, **kwargs):
        # Make the action
        what = 'WOSIBConnectFBCancelled'
        url = None
        app = None
        try:
            app = kwargs['app']
            url = kwargs['url']
        except Exception,e:
            logging.error(e, exc_info=True)

        uuid = generate_uuid( 16 )
        action = WOSIBConnectFBCancelled(
                key_name = uuid,
                uuid     = uuid,
                user     = user,
                app_     = app,
                url      = url,
                what = what
        )
        action.put()
        return action

class WOSIBFBConnected(UserAction):
    @staticmethod
    def create(user, **kwargs):
        # Make the action
        what = 'WOSIBFBConnected'
        url = None
        app = None
        try:
            app = kwargs['app']
            url = kwargs['url']
        except Exception,e:
            logging.error(e, exc_info=True)

        uuid = generate_uuid( 16 )
        action = WOSIBFBConnected(
                key_name = uuid,
                uuid     = uuid,
                user     = user,
                app_     = app,
                url      = url,
                what = what
        )
        action.put()
        return action

class WOSIBFriendChoosingCancelled(UserAction):
    @staticmethod
    def create(user, **kwargs):
        # Make the action
        what = 'WOSIBFriendChoosingCancelled'
        url = None
        app = None
        try:
            app = kwargs['app']
            url = kwargs['url']
        except Exception,e:
            logging.error(e, exc_info=True)

        uuid = generate_uuid( 16 )
        action = WOSIBFriendChoosingCancelled(
                key_name = uuid,
                uuid     = uuid,
                user     = user,
                app_     = app,
                url      = url,
                what = what
        )
        action.put()
        return action

class WOSIBNoConnectFBCancelled(UserAction):
    @staticmethod
    def create(user, **kwargs):
        # Make the action
        what = 'WOSIBNoConnectFBCancelled'
        url = None
        app = None
        try:
            app = kwargs['app']
            url = kwargs['url']
        except Exception,e:
            logging.error(e, exc_info=True)

        uuid = generate_uuid( 16 )
        action = WOSIBNoConnectFBCancelled(
                key_name = uuid,
                uuid     = uuid,
                user     = user,
                app_     = app,
                url      = url,
                what     = what
        )
        action.put()
        return action

class WOSIBNoConnectFBDialog(UserAction):
    @staticmethod
    def create(user, **kwargs):
        # Make the action
        what = 'WOSIBNoConnectFBDialog'
        url = None
        app = None
        try:
            app = kwargs['app']
            url = kwargs['url']
        except Exception,e:
            logging.error(e, exc_info=True)

        uuid = generate_uuid( 16 )
        action = WOSIBNoConnectFBDialog(
                key_name = uuid,
                uuid     = uuid,
                user     = user,
                app_     = app,
                url      = url,
                what = what
        )
        action.put()
        return action

class WOSIBConnectFBDialog(UserAction):
    @staticmethod
    def create(user, **kwargs):
        # Make the action
        what = 'WOSIBConnectFBDialog'
        url = None
        app = None
        try:
            app = kwargs['app']
            url = kwargs['url']
        except Exception,e:
            logging.error(e, exc_info=True)

        uuid = generate_uuid( 16 )
        action = WOSIBConnectFBDialog(
                key_name = uuid,
                uuid     = uuid,
                user     = user,
                app_     = app,
                url      = url,
                what = what
        )
        action.put()
        return action

class WOSIBUserAction(UserAction):
    wosib_instance = db.ReferenceProperty( db.Model, collection_name="wosib_user_actions" )

    ## Constructor
    @staticmethod
    def create(user, instance, what):
        # Make the action
        uuid = generate_uuid( 16 )
        act  = WOSIBUserAction(  key_name = uuid,
                                uuid     = uuid,
                                user     = user,
                                app_     = instance.app_,
                                link     = instance.link,
                                url      = instance.link.target_url,
                                what = what,
                                wosib_instance = instance)
        #super(WOSIBShowAction, act).create()
        act.put()
        return act
    
    def __str__(self):
        return '%s(%s) did %s to %s(%s) for wosib instance %s on site %s' % (
                self.user.get_full_name(), 
                self.user.uuid,
                self.what,
                self.wosib_instance.uuid,
                self.wosib_instance.app_.client.domain
        )

    ## Accessors 
    @staticmethod
    def get_by_instance(instance):
        return WOSIBUserAction.all().filter('wosib_instance =', instance)

    @staticmethod
    def get_by_app_and_instance_and_user(app, instance, user):
        return WOSIBUserAction.all().filter('app_ =', app)\
                                   .filter('wosib_instance =', instance)\
                                   .filter('user =', user)\
                                   .get()

    @staticmethod
    def get_by_app_and_instance(app, instance):
        return WOSIBUserAction.all().filter('app_ =', app)\
                                   .filter('wosib_instance =', instance).get()

