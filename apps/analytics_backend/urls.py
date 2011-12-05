#!/usr/bin/env python
from apps.analytics_backend.processes import EnsureHourlySlices

urlpatterns = [
    # Processes
    (r'/bea/EnsureHourlySlices', EnsureHourlySlices),
]
