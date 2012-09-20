#!/usr/bin/env python

from apps.analytics.processes import *
from apps.analytics.views import *

urlpatterns = [
    (r'/an/trackEvent', TrackEvent),

    # ideally we want this to be purely static
    (r'/an/tracking.js', TrackingJSLoader),
]
