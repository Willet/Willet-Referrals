#!/usr/bin/env python

#from apps.homepage.processes import *
from apps.homepage.views      import *

urlpatterns = [
    # The 'Shows' (aka GET)
    (r'/about',          ShowAboutPage),
    (r'/contact',        ShowAboutPage),
    (r'/dashboard/test', ShowDashboardTestPage),
    (r'/demo(.*)',       ShowDemoSitePage),
    (r'/()',             ShowLandingPage) # Must be last
]
