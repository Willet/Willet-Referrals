#!/usr/bin/env python

import logging

from google.appengine.api import memcache

from apps.action.models import ActionTally
from apps.user.models import User

from util.helpers import generate_uuid
from util.urihandler import obtain, URIHandler


class TrackTallyAction(URIHandler):
    """Increments action counts.

    In theory, also works with non-tally actions.
    """
    def get(self):
        """Let iframes/img tags track too."""
        self.post()

    def post(self):
        """Required parameter: evnt (backwards-compatible)"""
        evnt = self.request.get('evnt', '')
        if evnt:
            user = User.get_or_create_by_cookie(self)
            ActionTally.create(what=evnt, user=user)

        self.response.headers['Content-Type'] = 'image/gif'
        return


class TallyActions(URIHandler):
    """Saves memcached action tallies to the datastore."""
    def get(self):
        """Creates entries based on memcache status.

        If the memcache data is evicted at any point during the hour,
        data will not be accurate.

        For compatibility with the Action definition, "user" assigned
        will have nothing to do with the tally.

        The frequency of persistence is controlled by a cron job.
        Default: 1 hour
        """
        actions_to_persist = (memcache.get('actions_to_persist') or '')\
                             .split(',')

        for action in actions_to_persist:
            if action:  # could be empty string for some reason
                uuid = generate_uuid(16)
                try:
                    count = int(memcache.get(action))
                except TypeError:  # edgy: "None cannot become an Int"
                    count = 0  # action will not be saved thus
                logging.debug("count(%s) = %d" % (action, count))

                if count:  # died in memcache? 0?
                    act_obj = ActionTally(key_name=uuid,
                                          uuid=uuid,
                                          what=action,
                                          count=count)

                    act_obj.persist()
                    logging.debug('wrote a thing')
            memcache.set(action, 0)
        memcache.set('actions_to_persist', '')