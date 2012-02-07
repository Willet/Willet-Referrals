#!/usr/bin/env python

from apps.wosib.views     import *
from apps.wosib.processes import *

urlpatterns = [
    # Views
    (r'/w/js/jquery.colorbox.js',   WOSIBColorboxJSServer),
    (r'/w/ask.html',                WOSIBAskDynamicLoader),
    (r'/w/vote.html',               WOSIBVoteDynamicLoader),
    (r'/w/results.html',            WOSIBShowResults),
    (r'/w/fb_thanks.html',          WOSIBShowFBThanks),
    (r'/w/colorbox.css',            ShowWOSIBColorboxCSS),

    # Processes
    (r'/w/doVote',                  DoWOSIBVote),
    (r'/w/getExpired',              GetExpiredWOSIBInstances),
    (r'/w/instance/share/facebook', ShareWOSIBInstanceOnFacebook),
    (r'/s/sendFBMessages',          SendWOSIBFBMessages),
    (r'/w/removeExpired',           RemoveExpiredWOSIBInstance),
    (r'/w/instance/start',          StartWOSIBInstance),
    (r'/w/startPartialInstance',    StartPartialWOSIBInstance),
    (r'/w/track/showaction',        TrackWOSIBShowAction),
    (r'/w/track/useraction',        TrackWOSIBUserAction),
]
