#!/usr/bin/env python

from apps.wosib.views     import *
from apps.wosib.processes import *

urlpatterns = [
    # Views
    (r'/w/js/jquery.colorbox.js',   WOSIBColorboxJSServer),
    (r'/w/preask',                  WOSIBPreAskDynamicLoader),
    (r'/w/ask.html',                WOSIBAskDynamicLoader),
    (r'/w/vote.html',               WOSIBVoteDynamicLoader),
    (r'/w/results.html',            WOSIBShowResults),
    (r'/w/fb_thanks.html',          WOSIBShowFBThanks),
    (r'/w/track/unload',            ShowWOSIBUnloadHook),
    (r'/w/button_css',              ShowWOSIBButtonCSS),
    (r'/w/instance',                ShowWOSIBInstancePage), # query: id (instance ID)

    # Processes
    (r'/w/getExpired',              GetExpiredWOSIBInstances),
    (r'/w/instance/share/facebook', ShareWOSIBInstanceOnFacebook),
    (r'/w/instance/start',          StartWOSIBInstance),
    (r'/w/removeExpired',           RemoveExpiredWOSIBInstance),
    (r'/w/startPartialInstance',    StartPartialWOSIBInstance),
    (r'/w/track/showaction',        TrackWOSIBShowAction),
    (r'/w/track/useraction',        TrackWOSIBUserAction),
]
