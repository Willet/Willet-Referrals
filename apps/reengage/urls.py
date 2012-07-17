#!/usr/bin/env python
from apps.reengage.test_views import *

from apps.reengage.processes import *
from apps.reengage.resources import *
from apps.reengage.views import *

urlpatterns = [
    # Re-engage handlers (beta)
    (r'/r/shopify/?'              , ReEngageAppPage),
    (r'/r/shopify/welcome/?$'     , ReEngageLanding),
    (r'/r/shopify/instructions/?$', ReEngageInstructions),

    # Re-engage account handlers
    (r'/r/shopify/login/?$'       , ReEngageLogin),
    (r'/r/shopify/logout/?$'      , ReEngageLogout),
    (r'/r/shopify/account/create$', ReEngageCreateAccount),
    (r'/r/shopify/account/reset$' , ReEngageResetAccount),
    (r'/r/shopify/account/verify$', ReEngageVerify),

    # Re-engage Pseudo-resources
    (r'/r/shopify/queues$'           , ReEngageQueueHandler),
    (r'/r/shopify/queues\.json$'     , ReEngageQueueJSONHandler),
    (r'/r/shopify/product?$'        , ReEngageProductSourceHandler),
    (r'/r/shopify/product\.json$'   , ReEngageProductSourceJSONHandler),
    (r'/r/shopify/post/(\w+)$'      , ReEngagePostHandler),
    (r'/r/shopify/post/(\w+)\.json$', ReEngagePostJSONHandler),

    # Re-engage processes (beta)
    (r'/r/shopify/cron/?'         , ReEngageCron),
]