#!/usr/bin/env/python

# Actions for SIBT
# SIBTClickAction,
__author__ = "Willet, Inc."
__copyright__ = "Copyright 2011, Willet, Inc"

import datetime
import logging

from google.appengine.api import memcache
from google.appengine.ext import db
from google.appengine.datastore import entity_pb

from apps.action.models import Action
from apps.action.models import ClickAction
from apps.action.models import ShowAction
from apps.action.models import UserAction
from apps.action.models import VoteAction

from apps.gae_bingo.gae_bingo import bingo
from apps.product.models import Product

from util.helpers import generate_uuid
from util.consts import MEMCACHE_TIMEOUT

## ----------------------------------------------------------------------------
## SIBTClickAction Subclass ---------------------------------------------------
## ----------------------------------------------------------------------------
class SIBTClickAction(ClickAction):
    """ Designates a 'click' action for a User on a SIBT instance.
        Currently used for 'Referral' and 'SIBT' Apps """

    sibt_instance = db.ReferenceProperty(db.Model,
                                         collection_name="click_actions")

    # URL that was clicked on
    url = db.LinkProperty(indexed = True)

    def __str__(self):
        return 'SIBTCLICK: %s(%s) %s' % (self.user.get_full_name(),
                                         self.user.uuid,
                                         self.app_.uuid)

    ## Constructor
    @staticmethod
    def create(user, app, link):
        # Make the action
        uuid = generate_uuid(16)
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
            tracking = SIBTClickAction.get_tracking_by_user_and_app(user, app)
            actions = memcache.get_multi(tracking)

            for key in tracking:
                model = db.model_from_protobuf(entity_pb.EntityProto(actions.get(key)))
                logging.info('got tracking key: %s and model %s %s' % (
                    key,
                    model,
                    model.sibt_instance.key().id_or_name()
                ))
                if model.sibt_instance.key().id_or_name() in key_list:
                    break
                model = None
            if not model:
                model = SIBTClickAction.all()\
                    .filter('user =', user)\
                    .filter('url =', url)\
                    .filter('sibt_instance IN', key_list)\
                    .get()
        except Exception, e:
            logging.error('could not get model for instance: %s' % e, exc_info=True)
        return model

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

    sibt_instance = db.ReferenceProperty(db.Model, collection_name="vote_actions")

    # added if multi-product.
    product_uuid = db.StringProperty(indexed=True, required=False)

    # URL that was voted on
    url = db.LinkProperty(indexed = True)

    ## Constructor
    @staticmethod
    def create(user, instance, vote):
        """vote can be yes, no, or a product uuid."""
        # Make the action
        uuid = generate_uuid(16)

        try:
            # if vote is a product object (which is wrong)
            product_uuid = product.uuid
            logging.debug('product_uuid = %s? Is it right?' % product_uuid)
        except:
            logging.debug('product_uuid = %s' % vote)
            product_uuid = vote  # if vote is UUID (which is expected)

        action = SIBTVoteAction(key_name=uuid,
                                uuid=uuid,
                                user=user,
                                app_=instance.app_,
                                link=instance.link,
                                url=instance.link.target_url,
                                product_uuid=product_uuid,
                                sibt_instance=instance,
                                vote=vote)
        action.put()

        # we memcache by classname-instance_uuid-user_uuid
        # so we can look it up really easily later on
        memcache.set(action.get_tracking_key(),
                     action.get_key(),
                     time=MEMCACHE_TIMEOUT)

        return action

    def __str__(self):
        return 'SIBTVOTE: %s(%s) %s' % (self.user.get_full_name(),
                                        self.user.uuid,
                                        self.app_.uuid)

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
    def get_by_instance(instance):
        return SIBTVoteAction.all().filter('sibt_instance =', instance)

    @staticmethod
    def get_by_app_and_instance_and_user(app_, instance, user):
        action = None
        key = SIBTVoteAction.get_tracking_by_user_and_instance(user, instance)
        if key:
            action = SIBTVoteAction.get(key)

        if not action:
            action = SIBTVoteAction.all()\
                    .filter('app_ =', app_)\
                    .filter('sibt_instance =', instance)\
                    .filter('user =', user)\
                    .get()
        return action

    @staticmethod
    def get_by_app_and_instance(app_, instance):
        return SIBTVoteAction.all()\
                .filter('app_ =', app_)\
                .filter('sibt_instance =', instance)\
                .get()

class SIBTShowAction(ShowAction):
    sibt_instance = db.ReferenceProperty(db.Model, collection_name="show_actions")

    ## Constructor
    @staticmethod
    def create(user, instance, what):
        # Make the action
        uuid = generate_uuid(16)
        try:
            app_ = instance.app_
            link = instance.link
            url = instance.link.target_url
        except AttributeError:
            app_ = None
            link = None
            url = ''

        act = SIBTShowAction(key_name=uuid,
                             uuid=uuid,
                             user=user,
                             app_=instance.app_,
                             link=instance.link,
                             url=instance.link.target_url,
                             what=what,
                             sibt_instance=instance)
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
    def get_by_instance(instance):
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
        uuid = generate_uuid(16)
        action = SIBTShowingButton(key_name=uuid,
                                   uuid=uuid,
                                   user=user,
                                   app_=app,
                                   what=what,
                                   url=url)
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
                uuid = uuid,
                user = user,
                app_ = instance.app_,
                link = instance.link,
                url = instance.link.target_url,
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
                uuid = uuid,
                user = user,
                app_ = instance.app_,
                link = instance.link,
                url = instance.link.target_url,
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
                uuid = uuid,
                user = user,
                app_ = instance.app_,
                link = instance.link,
                url = instance.link.target_url,
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
        uuid = generate_uuid(16)
        action = SIBTVoteAction(
                key_name = uuid,
                uuid = uuid,
                user = user,
                app_ = instance.app_,
                link = instance.link,
                url = instance.link.target_url,
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

class SIBTVisitLength(UserAction):
    """action recording the length of visits (if onbeforeunload is called)."""
    @staticmethod
    def create(user, **kwargs):
        # Make the action
        what = 'SIBTVisitLength'
        url = None
        app = None
        duration= 0.0
        try:
            logging.debug ('kwargs for SIBTVisitLength: %s' % kwargs)
            app = kwargs['app']
            url = kwargs['url']
            duration = float (kwargs['duration'])
        except Exception,e:
            logging.error(e, exc_info=True)

        uuid = generate_uuid(16)
        action = SIBTVisitLength(
                key_name = uuid,
                uuid = uuid,
                user = user,
                app_ = app,
                url = url,
                what = what,
                duration = duration
        )
        action.put()

        return action

class SIBTInstanceCreated(SIBTInstanceAction):
    medium = db.StringProperty(default="", indexed=True)

    @staticmethod
    def create(user, **kwargs):
        what = 'SIBTInstanceCreated'
        medium = ""

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
                uuid = uuid,
                user = user,
                app_ = instance.app_,
                link = instance.link,
                url = instance.link.target_url,
                what = what,
                medium = medium,
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

class SIBTAskIframeCancelled(ShowAction):
    """ Cancelled immediately after opening - ie. no other actions in between open and close.
        Closed using "cancel' button on splash screen """
    @staticmethod
    def create(user, **kwargs):
        what = 'SIBTAskIframeCancelled'
        uuid = generate_uuid(16)

        # make sure we get an instance
        url = None
        app = None
        try:
            url = kwargs['url']
            app = kwargs['app']
        except Exception, e:
            logging.error('error getting url: %s' % e, exc_info=True)

        action = SIBTAskIframeCancelled(
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

class SIBTOverlayCancelled(ShowAction):
    """ Cancelled / closed iframe by clicking on the overlay (ie. outside of iframe) """
    @staticmethod
    def create(user, **kwargs):
        what = 'SIBTOverlayCancelled'
        uuid = generate_uuid(16)

        # make sure we get an instance
        url = None
        app = None
        try:
            url = kwargs['url']
            app = kwargs['app']
        except Exception, e:
            logging.error('error getting url: %s' % e, exc_info=True)

        action = SIBTOverlayCancelled(
                key_name = uuid,
                uuid = uuid,
                user = user,
                url = url,
                app_ = app,
                what = what
        )
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

        uuid = generate_uuid(16)
        action = SIBTUserClickedTopBarAsk(
                key_name = uuid,
                uuid = uuid,
                user = user,
                app_ = app,
                url = url,
                what = what
        )
        action.put()

        # Score bingo for bar or button
        bingo('sibt_bar_or_tab')

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

        uuid = generate_uuid(16)
        action = SIBTUserClickedButtonAsk(
                key_name = uuid,
                uuid = uuid,
                user = user,
                app_ = app,
                url = url,
                what = what
        )
        action.put()

        return action

class SIBTUserClickedOverlayAsk(UserAction):
    @staticmethod
    def create(user, **kwargs):
        # Make the action
        what = 'SIBTUserClickedOverlayAsk'
        url = None
        app = None
        try:
            app = kwargs['app']
            url = kwargs['url']
        except Exception,e:
            logging.error(e, exc_info=True)

        uuid = generate_uuid(16)
        action = SIBTUserClickedOverlayAsk(
                key_name = uuid,
                uuid = uuid,
                user = user,
                app_ = app,
                url = url,
                what = what
        )
        action.put()

        # Score bingo for bar or button
        bingo('sibt_overlay_style')

        return action

class SIBTUserClickedTabAsk(UserAction):
    @staticmethod
    def create(user, **kwargs):
        # Make the action
        what = 'SIBTUserClickedOverlayAsk'
        url = None
        app = None
        try:
            app = kwargs['app']
            url = kwargs['url']
        except Exception,e:
            logging.error(e, exc_info=True)

        uuid = generate_uuid(16)
        action = SIBTUserClickedOverlayAsk(
                key_name = uuid,
                uuid = uuid,
                user = user,
                app_ = app,
                url = url,
                what = what
        )
        action.put()

        # Score bingo for bar or button
        bingo('sibt_bar_or_tab')

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

        uuid = generate_uuid(16)
        action = SIBTUserClosedTopBar(
                key_name = uuid,
                uuid = uuid,
                user = user,
                app_ = app,
                url = url,
                what = what
        )
        action.put()
        return action

class SIBTUserReOpenedTopBar(UserAction):
    @staticmethod
    def create(user, **kwargs):
        # Make the action
        what = 'SIBTUserReOpenedTopBar'
        url = None
        app = None
        try:
            app = kwargs['app']
            url = kwargs['url']
        except Exception,e:
            logging.error(e, exc_info=True)

        uuid = generate_uuid(16)
        action = SIBTUserReOpenedTopBar(
                key_name = uuid,
                uuid = uuid,
                user = user,
                app_ = app,
                url = url,
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

        uuid = generate_uuid(16)
        action = SIBTAskUserClickedEditMotivation(
                key_name = uuid,
                uuid = uuid,
                user = user,
                app_ = app,
                url = url,
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

        uuid = generate_uuid(16)
        action = SIBTAskUserClickedShare(
                key_name = uuid,
                uuid = uuid,
                user = user,
                app_ = app,
                url = url,
                what = what
        )
        action.put()
        return action

class SIBTConnectFBCancelled(UserAction):
    @staticmethod
    def create(user, **kwargs):
        # Make the action
        what = 'SIBTConnectFBCancelled'
        url = None
        app = None
        try:
            app = kwargs['app']
            url = kwargs['url']
        except Exception,e:
            logging.error(e, exc_info=True)

        uuid = generate_uuid(16)
        action = SIBTConnectFBCancelled(
                key_name = uuid,
                uuid = uuid,
                user = user,
                app_ = app,
                url = url,
                what = what
        )
        action.put()
        return action

class SIBTFBConnected(UserAction):
    @staticmethod
    def create(user, **kwargs):
        # Make the action
        what = 'SIBTFBConnected'
        url = None
        app = None
        try:
            app = kwargs['app']
            url = kwargs['url']
        except Exception,e:
            logging.error(e, exc_info=True)

        uuid = generate_uuid(16)
        action = SIBTFBConnected(
                key_name = uuid,
                uuid = uuid,
                user = user,
                app_ = app,
                url = url,
                what = what
        )
        action.put()
        return action

class SIBTFriendChoosingCancelled(UserAction):
    @staticmethod
    def create(user, **kwargs):
        # Make the action
        what = 'SIBTFriendChoosingCancelled'
        url = None
        app = None
        try:
            app = kwargs['app']
            url = kwargs['url']
        except Exception,e:
            logging.error(e, exc_info=True)

        uuid = generate_uuid(16)
        action = SIBTFriendChoosingCancelled(
                key_name = uuid,
                uuid = uuid,
                user = user,
                app_ = app,
                url = url,
                what = what
        )
        action.put()
        return action

class SIBTNoConnectFBCancelled(UserAction):
    @staticmethod
    def create(user, **kwargs):
        # Make the action
        what = 'SIBTNoConnectFBCancelled'
        url = None
        app = None
        try:
            app = kwargs['app']
            url = kwargs['url']
        except Exception,e:
            logging.error(e, exc_info=True)

        uuid = generate_uuid(16)
        action = SIBTNoConnectFBCancelled(
                key_name = uuid,
                uuid = uuid,
                user = user,
                app_ = app,
                url = url,
                what = what
        )
        action.put()
        return action

class SIBTNoConnectFBDialog(UserAction):
    @staticmethod
    def create(user, **kwargs):
        # Make the action
        what = 'SIBTNoConnectFBDialog'
        url = None
        app = None
        try:
            app = kwargs['app']
            url = kwargs['url']
        except Exception,e:
            logging.error(e, exc_info=True)

        uuid = generate_uuid(16)
        action = SIBTNoConnectFBDialog(
                key_name = uuid,
                uuid = uuid,
                user = user,
                app_ = app,
                url = url,
                what = what
        )
        action.put()
        return action

class SIBTConnectFBDialog(UserAction):
    @staticmethod
    def create(user, **kwargs):
        # Make the action
        what = 'SIBTConnectFBDialog'
        url = None
        app = None
        try:
            app = kwargs['app']
            url = kwargs['url']
        except Exception,e:
            logging.error(e, exc_info=True)

        uuid = generate_uuid(16)
        action = SIBTConnectFBDialog(
                key_name = uuid,
                uuid = uuid,
                user = user,
                app_ = app,
                url = url,
                what = what
        )
        action.put()
        return action

class SIBTUserAction(UserAction):
    sibt_instance = db.ReferenceProperty(db.Model, collection_name="sibt_user_actions")

    ## Constructor
    @staticmethod
    def create(user, instance, what):
        # Make the action
        uuid = generate_uuid(16)
        act = SIBTUserAction( key_name = uuid,
                                uuid = uuid,
                                user = user,
                                app_ = instance.app_,
                                link = instance.link,
                                url = instance.link.target_url,
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

