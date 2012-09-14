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

        cohort = ReEngageCohort.get(cohort_uuid)
        label = cohort.queue.app_.client.url

        track_event(category, action, label, value)
