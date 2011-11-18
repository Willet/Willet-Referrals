#!/usr/bin/env python

from apps.sibt.views     import *
from apps.sibt.processes import *

urlpatterns = [
    # Views
    (r'/s/ask.html',            AskDynamicLoader),
    (r'/s/vote.html',           VoteDynamicLoader),
    (r'/s/results.html',        ShowResults),
    (r'/s/fb_thanks.html',      ShowFBThanks),
    (r'/s/startPartialInstance', StartPartialSIBTInstance),

    # Processes
    (r'/s/doVote',        DoVote),
    (r'/s/storeAnalytics', StoreAnalytics),
    (r'/s/instance/share/facebook', ShareSIBTInstanceOnFacebook),
    (r'/s/instance/start', StartSIBTInstance),
    (r'/s/getExpired',    GetExpiredSIBTInstances),
    (r'/s/removeExpired', RemoveExpiredSIBTInstance),
    (r'/s/track/showaction', TrackSIBTShowAction),
    (r'/s/track/useraction', TrackSIBTUserAction),
]
