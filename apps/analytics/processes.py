from apps.reengage.models import ReEngageCohort
from apps.analytics.utils import trackEvent
from util.consts import *

import logging

class TrackEvent(URIHandler):
    """Log incoming event"""
    def get(self):
        return self.post(self)

    def post(self):
        category = self.request.get('category')
        action = self.request.get('action')
        cohort_uuid = self.request.get('value')
        url = self.request.get('url')

        cohort = ReEngageCohort.get(cohort_uuid)
        label = cohort.queue.app_.client.url

        trackEvent(category, action, label, value)
