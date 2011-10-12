#!/usr/bin/env python

# Google App Engine Bingo
# modified to work with willet structure

from apps.gae_bingo import cache
from apps.gae_bingo import dashboard

urlpatterns = [
    ("/gae_bingo/persist", cache.PersistToDatastore),
    ("/gae_bingo/dashboard", dashboard.Dashboard),
    ("/gae_bingo/dashboard/control_experiment", dashboard.ControlExperiment),
]

