#!/usr/bin/env python
from apps.referrals.processes import *
from apps.referrals.views import *

urlpatterns = [
    (r'/conversion', PostConversion),
]


