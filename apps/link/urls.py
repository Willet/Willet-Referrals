#!/usr/bin/env python
from apps.link.processes import *
from apps.link.views import *

urlpatterns = [
    (r'/willet', DynamicLinkLoader),
    (r'/getTweets', getUncheckedTweets),
    (r'/(.*)', TrackWilltURL),
]
