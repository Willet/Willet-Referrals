#!/usr/bin/env python

from apps.sibt.views     import *
from apps.sibt.processes import *

urlpatterns = [
    # Views
    (r'/s/ask.html',      AskDynamicLoader),
    (r'/s/vote.html',     VoteDynamicLoader),

    # Processes
    (r'/s/doVote',        DoVote),
    (r'/s/storeAnalytics', DoStoreAnalytics),
    (r'/s/instance/share/facebook', ShareSIBTInstanceOnFacebook),
    (r'/s/instance/start', StartSIBTInstance),
    (r'/s/getExpired',    GetExpiredSIBTInstances),
    (r'/s/removeExpired', RemoveExpiredSIBTInstance)
]
