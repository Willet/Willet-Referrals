#!/usr/bin/env python
from apps.admin.processes import *
from apps.admin.views import *

urlpatterns = [
    (r'/admin', Admin),
    (r'/admin/plugin', ImportPlugin),
    (r'/admin/routes', ShowRoutes),
    (r'/admin/renamefb', RenameFacebookData),
    (r'/admin/renameinit', InitRenameFacebookData),
    (r'/admin/trackErr', TrackCallbackError),
    (r'/admin/manageApps', ManageApps),
    (r'/admin/ithinkiateacookie', TrackRemoteError),
    (r'/admin/sibt', SIBTInstanceStats),
    (r'/admin/install', InstallShopifyJunk),
]

