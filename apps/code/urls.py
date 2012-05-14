#!/usr/bin/env python

from apps.code.views import *
from apps.code.processes import *

urlpatterns = [
    # views
    (r'/code/list', ShowClientDiscountCodes),

    # processes
    (r'/code/import', ImportDiscountCodes)
]
