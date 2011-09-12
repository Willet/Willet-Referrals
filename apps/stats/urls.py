#!/usr/bin/env python

from apps.stats.processes import UpdateCounts, UpdateLanding, UpdateClicks, UpdateTweets
#from apps.stats.views import *

urlpatterns = [
    (r'/updateCounts', UpdateCounts),
    (r'/updateLanding', UpdateLanding),
    (r'/updateClicks',  UpdateClicks),
    (r'/updateTweets',  UpdateTweets), 
]
