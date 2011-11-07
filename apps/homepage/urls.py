#!/usr/bin/env python

#from apps.homepage.processes import *
from apps.homepage.views      import *

urlpatterns = [
    # The 'Shows' (aka GET)
    (r'/about',          ShowAboutPage),
    (r'/contact',        ShowAboutPage),
    (r'/dashboard/test', ShowDashboardTestPage),
    (r'/beta',           ShowBetaPage),
    (r'/more',           ShowMorePage),
    (r'/shopify',        ShowShopifyPage),
    (r'/privacy',        ShowPrivacyPage),
    (r'/terms',          ShowTermsPage),
    (r'/()',             ShowLandingPage) # Must be last
]
