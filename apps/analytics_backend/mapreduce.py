#!/usr/bin/env python

import logging

from mapreduce import operation

from apps.action.models import Action
from apps.analytics_backend.models import actions_to_count

def build_hourly_stats(time_slice):
    """this is our mapper"""
    start = time_slice.start
    end = time_slice.end
    logging.debug("Counting %d actions from %s to %s" % (
        len(actions_to_count), start, end))
    for action in actions_to_count:
        logging.debug("Counting for action: %s" % action)
        value = count_action(action, start, end)
        setattr(time_slice, action, value)

    yield operation.db.Put(time_slice)

def count_action(action, start, end):
    """Returns an Integer count for this action in the time period
    Note that with limit=None in the count() this operation will try to count
    all actions, but if it fails, it will time out."""
    return Action.all()\
        .filter('class =', action)\
        .filter('created >=', start)\
        .filter('created <', end)\
        .count(limit=None)

