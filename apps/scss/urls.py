#!/usr/bin/env python

from apps.scss.views import *

urlpatterns = [
    # views
    (r'/scss/(\w+).css', SCSSPathCompiler),
]
