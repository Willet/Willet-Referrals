#!/usr/bin/env python
from apps.analytics_backend.processes import *

urlpatterns = [
    # Processes
    (r'/bea/done/', AnalyticsDone),
    (r'/bea/(.*)/(.*)/', TimeSlices),
]
