from pyga.requests import Tracker, Session, Visitor
from pyga.entities import Event

import logging

def trackEvent(category, action, label=None, value=None):
    # ga.js equivalent. more or less.
    tracker = Tracker(GOOGLE_ANALYTICS_API_KEY, APP_DOMAIN)

    # dummy visitor and session for now.
	# not doing user analytics, just aggregate events
	visitor = Visitor()
	session = Session()

	event = Event(category=category, action=action, label=label, value=value)

	# send GA event to google & log
	tracker.track_event(ev, session, visitor)
    logging.info("Logged event: category=%s, action=%s, label=%s, value=%s" % (category, action, label, value))
