#!/usr/bin/env python
import logging

from apps.admin.processes import *
from apps.admin.views import *

urlpatterns = [
    # Views
    (r'/admin',                     ShowRoutes),
    (r'/admin/apps',                ManageApps),
    (r'/admin/actions',             ActionTallyDynamicLoader),
    (r'/admin/actions/since',       GetActionsSince),
    (r'/admin/reload_uris',         ReloadURIS),
    (r'/admin/memcache_console',    ShowMemcacheConsole),
    (r'/admin/check_mbc',           CheckMBC),
    (r'/admin/find',                RealFetch),
    (r'/admin/drz(/\w+)?(/\w+)?',   JohnFuckingZoidbergEditor),

    # Processes
    (r'/admin/sibt_reset/',             SIBTReset),
    (r'/admin/updateStore',             UpdateStore),
    (r'/admin/uploadEmailsToMailChimp', UploadEmailsToMailChimp),
    (r'/email/everyone',                EmailEveryone),
    (r'/email/someone',                 EmailSomeone),
    (r'/email/clientsidemessage',       ClientSideMessage),
    (r'/admin/db_integrity_check',      DBIntegrityCheck),
    (r'/admin/clean_old_actions',       CleanOldActions)
]