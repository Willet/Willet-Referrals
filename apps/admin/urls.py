#!/usr/bin/env python
import logging

from apps.admin.processes import *
from apps.admin.views import *

urlpatterns = [
    (r'/admin', Admin),
    (r'/admin/plugin', ImportPlugin),
    (r'/admin/routes', ShowRoutes),
    (r'/admin/renamefb', RenameFacebookData),
    (r'/admin/renameinit', InitRenameFacebookData),
    (r'/admin/trackErr', TrackCallbackError),
    (r'/admin/apps', ManageApps),
    (r'/admin/ithinkiateacookie', TrackRemoteError),
    (r'/admin/sibt', SIBTInstanceStats),
    (r'/admin/install', InstallShopifyJunk),
    (r'/admin/barbara', Barbara),
    (r'/admin/actions', ShowActions),
    (r'/admin/actions/since/', GetActionsSince),
    (r'/admin/click_actions', ShowClickActions),
    (r'/admin/fb_connect', FBConnectStats),
    (r'/admin/reload_uris', ReloadURIS),
    (r'/admin/memcache_console', MemcacheConsole),
    (r'/admin/check_mbc', CheckMBC),
    (r'/admin/updateStore', UpdateStore),
    (r'/admin/counts', ShowCounts),
    (r'/admin/analytics/rpc', AnalyticsRPC),
    (r'/admin/analytics/generate', GenerateOlderHourPeriods),
    (r'/admin/analytics/compare', AppAnalyticsCompare),
    (r'/admin/analytics/(.*)/', ShowAppAnalytics),
    (r'/admin/analytics/(.*)/rpc', AppAnalyticsRPC),
    (r'/admin/analytics', ShowAnalytics),
]

