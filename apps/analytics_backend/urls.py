#!/usr/bin/env python
from apps.analytics_backend.processes import *

urlpatterns = [
    # Processes
    (r'/a/appClicksCounter',    AppClicksCounter),
    (r'/a/triggerAppAnalytics', TriggerAppAnalytics),
    (r'/a/computeAppAnalytics', ComputeAppAnalytics),
]
