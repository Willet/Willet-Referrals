#!/usr/bin/env python

from apps.wosib.views     import *
from apps.wosib.processes import *

urlpatterns = [
    # Views
    (r'/w/js/jquery.colorbox.js',   WOSIBColorboxJSServer),
    (r'/w/track/unload',            ShowWOSIBUnloadHook),
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
