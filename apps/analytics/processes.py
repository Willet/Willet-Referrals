from util.urihandler import URIHandler
from apps.reengage.models import ReEngageCohort
from apps.analytics.utils import track_event
from util.consts import *

import logging

class TrackEvent(URIHandler):
    """Log incoming event"""
    def get(self):
        return self.post()

    def post(self):
        category = self.request.get('category')
        action = self.request.get('action')
        cohort_uuid = self.request.get('value')
        url = self.request.get('url')

        # google analytics only allows integer 'values'
        # as a quick fix, combine url and cohort id into the label
        # downside is that GA UI will be much less useful,
        # but we're still tracking all of the data
        label = "%s|%s" % (url, cohort_uuid)

        track_event(category, action, label)
