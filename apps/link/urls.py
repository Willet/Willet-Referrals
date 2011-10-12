#!/usr/bin/env python
from apps.link.processes import *
from apps.link.views import *

urlpatterns = [
    (r'/willet', DynamicLinkLoader),
    (r'/link/cleanBadLinks', CleanBadLinks),
    (r'/link/getTweets', getUncheckedTweets),
    (r'/link/init', InitCodes),
    (r'/link/incrementCodeCounter', IncrementCodeCounter),

    (r'/(.*)', TrackWilltURL),
]
