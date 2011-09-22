#!/usr/bin/env python

from apps.feedback.views      import *

urlpatterns = [
    # The 'Shows' (aka GET)
    (r'/feedback/add', AddFeedback),
]
