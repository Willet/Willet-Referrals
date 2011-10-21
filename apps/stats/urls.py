#!/usr/bin/env python

from apps.stats.processes import UpdateCounts
#from apps.stats.views import *

urlpatterns = [
    (r'/stats/updateCounts',  UpdateCounts),
]
