#!/usr/bin/env python
from apps.user.processes import *
from apps.user.views import *

urlpatterns = [
    #(r'/computeCampaignAnalytics', ComputeCampaignAnalytics),
    (r'/user/get/(.*)/', ShowProfileJSON),
    (r'/user/(.*)/(.*)/', ShowProfilePage),
    
    # processes
    (r'/updateEmailAddress', UpdateEmailAddress),
    (r'/fetchFB', FetchFacebookData),
    (r'/fetchFriends', FetchFacebookFriends),
    (r'/klout', QueryKloutAPI),
    (r'/socialGraphAPI', QueryGoogleSocialGraphAPI),
    (r'/tweet', UpdateTwitterGraph),  
    (r'/u/updateFBAccessToken', UpdateFBAccessToken),  
]

