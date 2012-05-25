#!/usr/bin/env python

from apps.action.processes import TrackShowAction

urlpatterns = [
    (r'/action/trackshowaction', TrackShowAction),
]
