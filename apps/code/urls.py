#!/usr/bin/env python

from apps.code.views import *
from apps.code.processes import *

urlpatterns = [
    # views
    (r'/code/list', ShowClientDiscountCodes),
    (r'/code/dispense', DispenseClientDiscountCode),
    (r'/code/test.css', SCSSTest),

    # processes
    (r'/code/import', ImportDiscountCodes)
]
