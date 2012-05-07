#!/usr/bin/env python

#from apps.homepage.processes import *
from apps.homepage.views import *

urlpatterns = [
    # The 'Shows' (aka GET)
    (r'/privacy',        ShowPrivacyPage),
    (r'/()',             ShowLandingPage) # Must be last
]