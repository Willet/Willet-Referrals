#!/usr/bin/env python
from apps.user.processes import *
from apps.user.views import *

urlpatterns = [
    #(r'/computeCampaignAnalytics', ComputeCampaignAnalytics),
    (r'/user/get/(.*)/', ShowProfileJSON),
    (r'/user/(.*)/(.*)/', ShowProfilePage),
    (r'/user/safariCookieHack', UserCookieSafariHack),
    
    # processes
    (r'/updateEmailAddress', UpdateEmailAddress),
    (r'/fetchFB', FetchFacebookData),
    (r'/fetchFriends', FetchFacebookFriends),
    (r'/socialGraphAPI', QueryGoogleSocialGraphAPI),
    (r'/u/updateFBAccessToken', UpdateFBAccessToken),  
]

