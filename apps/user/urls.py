#!/usr/bin/env python
from apps.user.processes import *
from apps.user.views import *

urlpatterns = [
    # Views
    #(r'/computeCampaignAnalytics', ComputeCampaignAnalytics),
    (r'/user/get/(.*)/', ShowProfileJSON),
    (r'/user/(.*)/(.*)/', ShowProfilePage),
    (r'/user/safariCookiePatch', UserCookieSafariHack),

    # Processes
    (r'/updateEmailAddress', UpdateEmailAddress),
    (r'/fetchFB', FetchFacebookData),
    (r'/fetchFriends', FetchFacebookFriends),
    (r'/socialGraphAPI', QueryGoogleSocialGraphAPI),
    (r'/u/updateFBAccessToken', UpdateFBAccessToken),
]
