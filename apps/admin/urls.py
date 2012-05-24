#!/usr/bin/env python
import logging

from apps.admin.processes import *
from apps.admin.views import *

urlpatterns = [
    # Views
    (r'/admin',                     Admin),
    (r'/admin/routes',              ShowRoutes),
    (r'/admin/apps',                ManageApps),
    (r'/admin/sibt',                SIBTInstanceStats),
    (r'/admin/actions',             ShowActions),
    (r'/admin/actions/since',       GetActionsSince),
    (r'/admin/reload_uris',         ReloadURIS),
    (r'/admin/memcache_console',    ShowMemcacheConsole),
    (r'/admin/check_mbc',           CheckMBC),
    (r'/admin/analytics/compare',   AppAnalyticsCompare),
    (r'/admin/analytics/(.*)/',     ShowAppAnalytics),
    (r'/admin/analytics',           ShowAnalytics),
    (r'/admin/find',                RealFetch),

    # Processes
    (r'/admin/analytics/generate',      GenerateOlderHourPeriods),
    (r'/admin/analytics/rpc',           AnalyticsRPC),
    (r'/admin/analytics/(.*)/rpc',      AppAnalyticsRPC),
    (r'/admin/ithinkiateacookie',       ClientSideMessage),
    (r'/admin/sibt_reset/',             SIBTReset),
    (r'/admin/updateStore',             UpdateStore),
    (r'/admin/uploadEmailsToMailChimp', UploadEmailsToMailChimp),
    (r'/email/everyone',                EmailEveryone),
    (r'/email/someone',                 EmailSomeone),
    (r'/admin/db_integrity_check',      DBIntegrityCheck)
]