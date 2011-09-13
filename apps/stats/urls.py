#!/usr/bin/env python

from apps.stats.processes import UpdateCounts, UpdateClicks, UpdateTweets
#from apps.stats.views import *

urlpatterns = [
    (r'/stats/updateCounts',  UpdateCounts),
    (r'/stats/updateClicks',  UpdateClicks),
    (r'/stats/updateTweets',  UpdateTweets), 
]
