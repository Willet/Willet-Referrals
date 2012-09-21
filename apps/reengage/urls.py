#!/usr/bin/env python

from apps.reengage.processes import *
from apps.reengage.resources import *
from apps.reengage.views import *

urlpatterns = [
    # Re-engage handlers (beta)
    (r'/r/reengage/js/com.js', ReEngageCPLServeScript),
    (r'/r/shopify/beta/?', ReEngageAppPage),
    (r'/r/shopify/welcome/?', ReEngageShopifyWelcome),  # TODO: move to shopify subfolder
    (r'/r/shopify/instructions/?', ReEngageInstructions),
    (r'/r/shopify/how_to/?', ReEngageHowTo),
    (r'/r/setup_fb/?', ReEngageSetupFB),
    (r'/r/shopify/analytics/?', ReEngageAnalyticsPage),

    # Re-engage account handlers
    (r'/r/shopify/login/?', ReEngageLogin),
    (r'/r/shopify/logout/?', ReEngageLogout),
    (r'/r/shopify/account/create', ReEngageCreateAccount),
    (r'/r/shopify/account/reset', ReEngageResetAccount),
    (r'/r/shopify/account/verify', ReEngageVerify),

    # Re-engage Pseudo-resources
    (r'/r/shopify/queues$', ReEngageQueueHandler),
    (r'/r/shopify/queue\.json', ReEngageQueueJSONHandler),
    (r'/r/shopify/queues\.json', ReEngageQueuesJSONHandler),
    (r'/r/shopify/product?', ReEngageProductSourceHandler),
    (r'/r/shopify/product\.json', ReEngageProductSourceJSONHandler),
    (r'/r/shopify/post/(\w+)', ReEngagePostHandler),
    (r'/r/shopify/post/(\w+)\.json', ReEngagePostJSONHandler),

    # Re-engage processes (beta)
    (r'/r/shopify/cron/start/?', ReEngageCron),
    (r'/r/shopify/cron/plan/?', ReEngageStartMarketingPlan),
    (r'/r/shopify/cron/post/?', ReEngageCronPostMessage),
    (r'/r/shopify/cron/snippets/?', ReEngageUpdateSnippets),
]
