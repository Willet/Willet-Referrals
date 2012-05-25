#!/usr/bin/env/python

"""Actions for SIBT."""

__author__ = "Willet, Inc."
__copyright__ = "Copyright 2011, Willet, Inc"

import logging

from google.appengine.api import memcache
from google.appengine.ext import db
from google.appengine.datastore import entity_pb

from apps.action.models import ClickAction, ShowAction, VoteAction

from util.consts import MEMCACHE_TIMEOUT
from util.helpers import generate_uuid


class SIBTClickAction(ClickAction):
    """ Designates a 'click' action for a User on a SIBT instance.
        Currently used for 'Referral' and 'SIBT' Apps """

    sibt_instance = db.ReferenceProperty(db.Model,
                                         collection_name="click_actions")

    # URL that was clicked on
    url = db.LinkProperty(indexed=True)

    def __str__(self):
        return 'SIBTCLICK: %s(%s) %s' % (self.user.get_full_name(),
                                         self.user.uuid,
                                         self.app_.uuid)

    ## Constructor
    @staticmethod
    def create(user, app, link):
        # Make the action
        uuid = generate_uuid(16)
        action = SIBTClickAction(key_name=uuid, uuid=uuid, user=user,
                                 app_=app, link=link, url=link.target_url,
                                 sibt_instance=link.sibt_instance.get())
        action.put()

        tracking_keys = memcache.get(action.get_tracking_key()) or []
        tracking_keys.append(action.get_key())
        memcache.set(action.get_tracking_key(), tracking_keys,
                     time=MEMCACHE_TIMEOUT)

        return action

    ## Accessors
    @staticmethod
    def get_for_instance(app, user, url, key_list):
        logging.debug('getting action for:\napp: %s\nuser: %s\n'
                      'url: %s\nkeys: %s' % (app, user, url, key_list))
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
            logging.error('could not get model for instance: %s' % e,
                          exc_info=True)
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
        return '%s-%s-%s' % (self.__class__.__name__, self.app_.uuid,
                             self.user.uuid)


class SIBTVoteAction(VoteAction):
    """ Designates a 'vote' action for a User on a SIBT instance.
        Currently used for 'SIBT' App """

    sibt_instance = db.ReferenceProperty(db.Model,
                                         collection_name="vote_actions")

    # added if multi-product.
    product_uuid = db.StringProperty(indexed=True, required=False)

    # URL that was voted on
    url = db.LinkProperty(indexed=True)

    ## Constructor
    @staticmethod
    def create(user, instance, vote):
        """vote can be yes, no, or a product uuid."""
        # Make the action
        uuid = generate_uuid(16)

        try:
            # if vote is a product object (which is wrong)
            product_uuid = vote.uuid
            vote = 'yes'  # fix vote to be text, not object
            logging.debug('product_uuid = %s? Is it right?' % product_uuid)
        except:
            logging.debug('product_uuid = %s' % vote)
            product_uuid = vote  # if vote is UUID (which is expected)

        action = SIBTVoteAction(key_name=uuid, uuid=uuid, user=user,
                                app_=instance.app_, link=instance.link,
                                url=instance.link.target_url,
                                product_uuid=product_uuid,
                                sibt_instance=instance, vote=vote)
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
    sibt_instance = db.ReferenceProperty(db.Model,
                                         collection_name="show_actions")

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

        act = SIBTShowAction(key_name=uuid, uuid=uuid, user=user, app_=app_,
                             link=link, url=url, what=what,
                             sibt_instance=instance)
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
        action = SIBTShowingButton(key_name=uuid, uuid=uuid, user=user,
                                   app_=app, what=what, url=url)
        action.put()

        # tracking urls for fast lookup
        tracking_urls = memcache.get(action.get_tracking_key()) or []
        tracking_urls.append(url)
        memcache.set(action.get_tracking_key(), tracking_urls,
                     time=MEMCACHE_TIMEOUT)
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
        return '%s-%s-%s' % (self.__class__.__name__, self.app_.uuid,
                             self.user.uuid)
