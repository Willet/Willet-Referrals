#!/usr/bin/env python

import logging

from google.appengine.api import memcache

from apps.action.models import ActionTally
from apps.user.models import User

from util.helpers import generate_uuid
from util.urihandler import obtain, URIHandler


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
        user = User.get_or_create_by_cookie(self)

        for action in actions_to_persist:
            if action:  # could be empty string for some reason
                uuid = generate_uuid(16)
                count = int(memcache.get(action)) or 0
                logging.debug("count(%s) = %d" % (action, count))
                if count:  # died in memcache? 0?
                    act_obj = ActionTally(key_name=uuid,
                                          uuid=uuid,
                                          what=action,
                                          count=count,
                                          user=user)

                    act_obj.persist()
                    logging.debug('wrote a thing')
            memcache.set(action, 0)
        memcache.set('actions_to_persist', '')