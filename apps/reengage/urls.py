#!/usr/bin/env python
from apps.reengage.test_views import *

from apps.reengage.processes import *
from apps.reengage.resources import *
from apps.reengage.views import *

urlpatterns = [
    # Test URLs
    (r'/reengage/(fb|t)?'         , ReEngageControlPanel),
    (r'/reengage/post/(fb|t)?'    , ReEngage),
    (r'/reengage/product'         , ReEngageProduct),
    (r'/reengage/find_tweet'      , ReEngageFindTweet),

    # Re-engage handlers (beta)
    (r'/r/reengage/js/com.js'     , ReEngageCPLServeScript),
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
    (r'/r/shopify/queue$'           , ReEngageQueueHandler),
    (r'/r/shopify/queue\.json$'     , ReEngageQueueJSONHandler),
    (r'/r/shopify/product?$'        , ReEngageProductSourceHandler),
    (r'/r/shopify/product\.json$'   , ReEngageProductSourceJSONHandler),
    (r'/r/shopify/post/(\w+)$'      , ReEngagePostHandler),
    (r'/r/shopify/post/(\w+)\.json$', ReEngagePostJSONHandler),

    # Re-engage processes (beta)
    (r'/r/shopify/cron/?'         , ReEngageCron),
]