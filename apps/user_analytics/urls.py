#!/usr/bin/env python
from apps.user_analytics.processes import *
from apps.user_analytics.views import *

urlpatterns = [
    (r'/user_analytics/trigger', TriggerUserAnalytics),
    (r'/user_analytics/compute', ComputeUserAnalytics),
]
