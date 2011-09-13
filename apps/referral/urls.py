#!/usr/bin/env python

from apps.referral.processes import *
from apps.referral.views     import *

urlpatterns = [
    # Views
    (r'/r/code',             ShowCodePage),
    (r'/r/edit',             ShowEditPage),
    (r'/r/campaign/(.*)/',   ShowDashboard),
    (r'/r/doUpdateOrCreate', DoUpdateOrCreate),

    # Processes
    (r'/r/emailerCron',      EmailerCron),
    (r'/r/emailerQueue',     EmailerQueue),
    (r'/r/conversion',       PostConversion),
]
