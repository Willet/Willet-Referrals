#!/usr/bin/env python

from apps.sibt.views import *
from apps.sibt.processes import *

urlpatterns = [
    # Views
    (r'/s/js/jquery.colorbox.js',   ColorboxJSServer),
    (r'/s/ask.html',                AskDynamicLoader),
    (r'/s/vote.html',               VoteDynamicLoader),
    (r'/s/results.html',            ShowResults),
    (r'/s/fb_thanks.html',          ShowFBThanks),
    (r'/s/track/unload',            ShowOnUnloadHook),
    (r'/s/sibt.js',                 SIBTServeScript),
    (r'/s/beta',                    ShowBetaPage),
    (r'/s/beta/signup',             SIBTSignUp),

    # Processes
    (r'/s/doVote',                  DoVote),
    (r'/s/getExpired',              GetExpiredSIBTInstances),
    (r'/s/instance/share/facebook', ShareSIBTInstanceOnFacebook),
    (r'/s/instance/start',          StartSIBTInstance),
    (r'/s/removeExpired',           RemoveExpiredSIBTInstance),
    (r'/s/sendFriendAsks',          SendFriendAsks),
    (r'/s/startPartialInstance',    StartPartialSIBTInstance),
    (r'/s/track/showaction',        TrackSIBTShowAction),
    (r'/s/track/useraction',        TrackSIBTUserAction),
]
