#!/usr/bin/env python

from apps.action.processes import TallyActions, TrackTallyAction

urlpatterns = [
    (r'/a/tally', TallyActions),
    (r'/a/tally/track', TrackTallyAction),
]