#!/usr/bin/env python
from apps.user_analytics.processes import *
from apps.user_analytics.views import *

urlpatterns = [
    (r'/user/triggerUserAnalytics', TriggerUserAnalytics),
    (r'/user/computeUserAnalytics', ComputeUserAnalytics),
]
