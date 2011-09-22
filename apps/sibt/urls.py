#!/usr/bin/env python

from apps.sibt.views     import *

urlpatterns = [
    (r'/s/ask.html',     DynamicLoader),
]
