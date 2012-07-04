#!/usr/bin/env/python

"""The Action Model.

A parent class for all User actions e.g. ClickAction, VoteAction, ViewAction
"""

__author__ = "Willet, Inc."
__copyright__ = "Copyright 2012, Willet, Inc"

import logging

from google.appengine.api import memcache
from google.appengine.ext import db
from google.appengine.ext.db import polymodel

from util.errors import deprecated
from util.helpers import generate_uuid
from util.memcache_ref_prop import MemcacheReferenceProperty
from util.model import Model


class Action(Model, polymodel.PolyModel):
    """ Whenever a 'User' completes a Willet Action,
        an 'Action' obj will be stored for them.
        This 'Action' class will be subclassed for specific actions
        ie. click, vote, tweet, share, email, etc.
    """

    # Datetime when this model was put into the DB
    created = db.DateTimeProperty(auto_now_add=True)
    # Length of time a compound action had persisted prior to its creation
    duration = db.FloatProperty(default=0.0)
    # Person who did the action
    user = MemcacheReferenceProperty(db.Model, collection_name='user_actions')
    # True iff this Action's User is an admin
    is_admin = db.BooleanProperty(default=False)
    # The App that this Action is for
    app_ = db.ReferenceProperty(db.Model, collection_name='app_actions')

    def __init__(self, *args, **kwargs):
        self._memcache_key = kwargs['uuid'] if 'uuid' in kwargs else None
        super(Action, self).__init__(*args, **kwargs)

    def _validate_self(self):
        if self.duration < 0:
            raise ValueError('duration cannot be less than 0 seconds')

        return True

    def put(self):
        self.put_later()

    def get_class_name(self):
        return self.__class__.__name__
    name = property(get_class_name)

    def _validate_self(self):
        return True

    def __unicode__(self):
        return self.__str__()

    def __str__(self):
        # Subclasses should override this
        return "%s %s" % (self.__class__.__name__, self.uuid)


class ActionTally(Action):
    """An ActionTally (if there isn't a better name) is an Action
    object that isn't written until the end of the hour, and within it
    is a "count" property that describes how many creation attempts
    were done to this action.

    Say if two ActionTally.create()s were called over the past time period,
    the ActionTally object of the hour will contain a count of 2.

    The frequency of persistence is controlled by a cron job.
    Default: 5 mins
    """
    what = db.StringProperty(indexed=True)
    count = db.IntegerProperty(indexed=False, default=0)

    @classmethod
    def create(cls, **kwargs):
        """If superclass does not have one of those..."""
        uuid = generate_uuid(16)

        kwargs.update({'key_name': uuid,
                       'uuid': uuid,
                       'what': kwargs.get('what', cls.__name__)})

        action = cls(**kwargs)
        action.put()  # defaults to delay put

    def put(self):
        """a tally does not write itself, merely incrementing its
        memcache value.
        """
        # update the list of actions the cron needs to write next hour.
        actions_to_persist = (memcache.get('actions_to_persist') or '')\
                             .split(',')
        actions_to_persist.append(self.what or self.__class__.__name__)
        actions_to_persist = list(frozenset(actions_to_persist))
        memcache.set('actions_to_persist', ','.join(actions_to_persist))

        # increment the count for this action.
        memcache.incr(self.what or self.__class__.__name__,
                      initial_value=0)

    def persist(self):
        """writes this class into the db. Sometimes called hard_put()."""
        super(self.__class__, self).put()


class ClickAction(ActionTally):
    """ Designates a 'click' action for a User.
        Currently used for 'SIBT' and 'WOSIB' Apps
    """

    # Link that caused the click action ...
    link = db.ReferenceProperty(db.Model, collection_name = "link_clicks")

    def __init__(self, *args, **kwargs):
        super(ClickAction, self).__init__(*args, **kwargs)

        # Tell Mixplanel that we got a click
        #self.app_.storeAnalyticsDatum(self.class_name(), self.user, self.link.target_url)

    def __str__(self):
        return 'CLICK: %s(%s) %s' % (
                self.user.get_full_name(),
                self.user.uuid,
                self.app_.uuid
        )


class VoteAction(ActionTally):
    """Designates a 'vote' action for a User.

    Primarily used for 'SIBT' App.
    """

    # Link that caused the vote action ...
    link = db.ReferenceProperty(db.Model, collection_name = "link_votes")

    # Typically 'yes' or 'no'; occasionally product uuids
    vote = db.StringProperty(indexed = True)

    def __init__(self, *args, **kwargs):
        super(VoteAction, self).__init__(*args, **kwargs)

    def __str__(self):
        return 'VOTE: %s(%s) %s' % (self.user.get_full_name(), self.user.uuid,
                                    self.app_.uuid)

    def _validate_self(self):
        return True


class LoadAction(ActionTally):
    pass


class ScriptLoadAction(LoadAction):
    pass


class ButtonLoadAction(LoadAction):
    pass


class ShowAction(ActionTally):
    """We are showing something ..."""

    # url/page this was shown on
    url = db.LinkProperty(indexed=False)

    @staticmethod
    def create(user, app, what, url):
        uuid = generate_uuid(16)
        action = ShowAction(key_name=uuid,
                            uuid=uuid,
                            user=user,
                            app_=app,
                            what=what,
                            url=url)

        action.put()
        return action

    def __str__(self):
        return 'Showing %s to %s on %s' % (
            self.what,
            self.user.get_first_name(),
            self.url,
        )


class UserAction(ActionTally):
    """A user action, such as clicking on a button or something like that"""
    pass