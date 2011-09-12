#!/usr/bin/env python
from apps.link.processes import *
from apps.link.views import *

urlpatterns = [
    (r'/willet', DynamicLoader),
    (r'/(.*)', TrackWilltURL)
]
