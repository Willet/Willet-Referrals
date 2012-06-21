#!/usr/bin/env/python

"""The Action Model.

A parent class for all User actions e.g. ClickAction, VoteAction, ViewAction
"""

__author__ = "Willet, Inc."
__copyright__ = "Copyright 2012, Willet, Inc"

import logging

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
    duration = db.FloatProperty(default = 0.0)
    # Person who did the action
    user = MemcacheReferenceProperty(db.Model, collection_name='user_actions')
    # True iff this Action's User is an admin
    is_admin = db.BooleanProperty(default=False)
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
        pass

    @deprecated
    @classmethod
    def count(cls, admins_too=False):
        pass
        '''
        if admins_too:
            return cls.all().count()
        else:
            return cls.all().filter('is_admin =', False).count()
        '''

    @deprecated
    @staticmethod
    def get_by_user(user):
        """Not indexed; will not work."""
        # return Action.all().filter('user =', user).get()

    @deprecated
    @staticmethod
    def get_by_app(app, admins_too = False):
        """Not indexed; will not work."""
        '''
        app_actions = Action.all().filter('app_ =', app)
        if admins_too:
            return app_actions.get()
        else:
            return app_actions.filter('is_admin =', False).get()
        '''


class ClickAction(Action):
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


class VoteAction(Action):
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

    @deprecated
    @classmethod
    def get_by_vote(cls, vote):
        """Not indexed; will not work."""
        return cls.all().filter('vote =', vote)

    @deprecated
    @classmethod
    def get_all_yesses(cls):
        return cls.get_by_vote('yes')

    @deprecated
    @classmethod
    def get_all_nos(cls):
        return cls.get_by_vote('no')


class LoadAction(Action):
    pass


class ScriptLoadAction(LoadAction):
    pass


class ButtonLoadAction(LoadAction):
    pass


class ShowAction(Action):
    """We are showing something ..."""

    # what we are showing... dumb but true!
    what = db.StringProperty()

    # url/page this was shown on
    url = db.LinkProperty(indexed=True)

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


class UserAction(Action):
    """A user action, such as clicking on a button or something like that"""
    pass