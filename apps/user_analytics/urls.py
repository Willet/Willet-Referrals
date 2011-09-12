#!/usr/bin/env python
from apps.user_analytics.processes import *
from apps.user_analytics.views import *

urlpatterns = [
    #(r'/computeCampaignAnalytics', ComputeCampaignAnalytics),
    (r'/triggerUserAnalytics', TriggerUserAnalytics),
    (r'/computeUserAnalytics', ComputeUserAnalytics),
]
