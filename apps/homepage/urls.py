#!/usr/bin/env python
from apps.homepage.processes import *
from apps.homepage.views import *

urlpatterns = [
    #(r'/computeCampaignAnalytics', ComputeCampaignAnalytics),
    (r'/about', ShowAboutPage),
    (r'/contact', ShowAboutPage),
    (r'/dashboard/test', ShowDashboardTestPage),
    (r'/demo(.*)',ShowDemoSitePage),
    (r'/()', ShowLandingPage)
]
