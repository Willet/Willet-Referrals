#!/usr/bin/env python

from apps.analytics.processes import *

urlpatterns = [
    (r'/an/trackEvent', TrackEvent),
]
