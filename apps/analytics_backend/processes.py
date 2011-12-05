#!/usr/env/python

#import logging
import datetime

from google.appengine.ext import webapp

from apps.analytics_backend.models import AnalyticsHourSlice

class EnsureHourlySlices(webapp.RequestHandler):
    def get(self):
        today = datetime.datetime.today()
        for hour in range(24):
            val = today - datetime.timedelta(hours=hour)
            # Ensure the existence of, or trigger the creation of any missing Hour entities
            # This, and any similar entitiy creation methods, must be idempotent
            AnalyticsHourSlice.get_or_create(start=val)

