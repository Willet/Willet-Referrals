#!/usr/bin/env python
from apps.user.processes import *
from apps.user.views import *

urlpatterns = [
    #(r'/computeCampaignAnalytics', ComputeCampaignAnalytics),
    (r'/campaign/get_user/(.*)/(.*)/', ShowProfilePage),
    (r'/profile/(.*)/(.*)/', ShowProfilePage),
    
    # processes
    (r'/fetchFB', FetchFacebookData),
    (r'/fetchFriends', FetchFacebookFriends),
]

