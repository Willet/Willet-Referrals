from util.consts import GOOGLE_ANALYTICS_API_KEY, APP_DOMAIN

from pyga.entities import Event
from pyga.requests import Tracker, Session, Visitor

import logging


def track_event(category, action, label=None, value=None):
    """Save the event to our event backend.

    Currently the only event backend supported is Google Analytics.
    """
    tracker = Tracker(GOOGLE_ANALYTICS_API_KEY, APP_DOMAIN)

    # dummy visitor and session for now.
    # not doing user analytics, just aggregate events
    visitor = Visitor()
    session = Session()

    event = Event(category=category, action=action, label=label, value=value)

    # send GA event to google & log
    tracker.track_event(event, session, visitor)
    logging.info("Logged event: category=%s, action=%s, label=%s, value=%s",
                 category, action, label, value)
