#!/usr/bin/env/python

"""Actions for SIBT. DEPRECATED."""

__author__ = "Willet, Inc."
__copyright__ = "Copyright 2012, Willet, Inc"

import logging

from google.appengine.api import memcache
from google.appengine.ext import db

from apps.action.models import ClickAction, ShowAction, UserAction, VoteAction

from util.consts import MEMCACHE_TIMEOUT
from util.errors import deprecated
from util.helpers import generate_uuid


class SIBTUserAction(UserAction):
    """Records what a user does.

    All subclasses are deprecated; its own use is also discouraged.

    All parameters are optional. Some subclasses (e.g. SIBTVisitLength)
    will require additional keyword arguments (e.g. duration) to be meaningful.
    """
    sibt_instance = db.ReferenceProperty(db.Model,
                                         collection_name="sibt_user_actions")

    @classmethod
    def create(cls, user, instance=None, what='', **kwargs):
        """Make the action."""
        uuid = generate_uuid(16)

        if instance:
            kwargs.update({
                'key_name': uuid,
                'uuid': uuid,
                'user': user,
                'app_': instance.app_,
                'link': instance.link,
                'url': instance.link.target_url,
                'what': cls.__name__,
                'sibt_instance': instance
            })
        else:
            kwargs.update({
                'key_name': uuid,
                'uuid': uuid,
                'user': user,
                'what': cls.__name__
            })

        act = cls(**kwargs)
        act.put()
        return act

    def __str__(self):
        return '%s %s' % (self.__class__.__name__,
                          self.uuid)


class SIBTClickAction(ClickAction):
    pass


class SIBTVoteAction(VoteAction):
    """ Designates a 'vote' action for a User on a SIBT instance.
        Currently used for 'SIBT' App """

    sibt_instance = db.ReferenceProperty(db.Model,
                                         collection_name="vote_actions")

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
            product_uuid = vote.uuid
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
        return '%s-%s-%s' % (self.__class__.__name__,
                             self.sibt_instance.uuid,
                             self.user.uuid)

    @deprecated
    @staticmethod
    def get_by_instance(instance):
        return instance.vote_actions


    @staticmethod
    def get_by_app_and_instance_and_user(app_, instance, user):
        """This is not indexed. How does it even work?"""
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


class SIBTShowAction(ShowAction):
    pass


class SIBTShowingButton(ShowAction):
    """To be replaced by cookies later."""

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
        tracking_key = '%s-%s-%s' % (cls.__name__,
                                     app.uuid,
                                     user.uuid)
        return memcache.get(tracking_key) or []

    def get_tracking_key(self):
        return '%s-%s-%s' % (self.__class__.__name__,
                             self.app_.uuid,
                             self.user.uuid)


class SIBTShowingResults(SIBTShowAction):
    pass


class SIBTShowingResultsToAsker(SIBTShowAction):
    pass


class SIBTShowingVote(SIBTShowAction):
    pass


class SIBTInstanceAction(UserAction):
    pass


class SIBTVisitLength(UserAction):
    """Unique kwargs: duration <float>."""
    pass


class SIBTInstanceCreated(SIBTInstanceAction):
    pass


class SIBTShowingAskIframe(ShowAction):
    pass


class SIBTAskIframeCancelled(ShowAction):
    pass


class SIBTOverlayCancelled(ShowAction):
    pass


class SIBTShowingTopBarAsk(ShowAction):
    pass


class SIBTShowingAskTopBarIframe(ShowAction):
    pass


class SIBTUserClickedTopBarAsk(UserAction):
    pass


class SIBTUserClickedButtonAsk(UserAction):
    pass


class SIBTUserClickedOverlayAsk(UserAction):
    pass


class SIBTUserClickedTabAsk(UserAction):
    pass


class SIBTUserClosedTopBar(UserAction):
    pass


class SIBTUserReOpenedTopBar(UserAction):
    pass


class SIBTAskUserClickedEditMotivation(UserAction):
    pass


class SIBTAskUserClickedShare(UserAction):
    pass


class SIBTConnectFBCancelled(UserAction):
    pass


class SIBTFBConnected(UserAction):
    pass


class SIBTFriendChoosingCancelled(UserAction):
    pass


class SIBTNoConnectFBCancelled(UserAction):
    pass


class SIBTNoConnectFBDialog(UserAction):
    pass


class SIBTConnectFBDialog(UserAction):
    pass