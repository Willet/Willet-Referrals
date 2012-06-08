#!/usr/bin/env python
from apps.link.processes import *
from apps.link.views import *

urlpatterns = [
    (r'/link/cleanBadLinks', CleanBadLinks),
    (r'/link/init', InitCodes),
    (r'/link/create', CreateLink),
    (r'/link/incrementCodeCounter', IncrementCodeCounter),

    (r'/(.*)', TrackWilltURL),
]