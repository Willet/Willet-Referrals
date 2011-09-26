#!/usr/bin/env python

# Google App Engine Bingo
# modified to work with willet structure

from apps.gae_bingo.tests import RunStep

urlpatterns = [
    ("/gae_bingo/tests/run_step", RunStep),
]

