#!/usr/bin/env python

from util.urihandler import DeprecationHandler

urlpatterns = [
    (r'/a/tally', DeprecationHandler),
    (r'/a/tally/track', DeprecationHandler),
]