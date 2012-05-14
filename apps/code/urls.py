#!/usr/bin/env python

from apps.code.views import *

urlpatterns = [
    (r'/code/list', ShowClientDiscountCodes)
]
