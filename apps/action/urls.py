#!/usr/bin/env python

from apps.action.processes import TallyActions

urlpatterns = [
    (r'/a/tally', TallyActions),
]