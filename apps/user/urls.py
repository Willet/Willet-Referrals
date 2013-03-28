#!/usr/bin/env python
from apps.user.processes import *
from apps.user.views import *
from util.urihandler import DeprecationHandler

urlpatterns = [
    # Views
    (r'/user/get/(.*)/', ShowProfileJSON),
    (r'/user/(.*)/(.*)/', ShowProfilePage),
    (r'/user/safariCookiePatch', DeprecationHandler),

    # Processes
    (r'/updateEmailAddress', UpdateEmailAddress),
    (r'/fetchFB', FetchFacebookData),
    (r'/fetchFriends', FetchFacebookFriends),
    (r'/socialGraphAPI', QueryGoogleSocialGraphAPI),
]
