#!/usr/bin/env python
from apps.reengage.processes import *
from apps.reengage.test_views import *
from apps.reengage.views import *

urlpatterns = [
    # Test URLs
    (r'/reengage/(fb|t)?',      ReEngageControlPanel),
    (r'/reengage/post/(fb|t)?', ReEngage),
    (r'/reengage/product',      ReEngageProduct),
    (r'/reengage/find_tweet',   ReEngageFindTweet),

    # Re-engage handlers (beta)
    (r'/r/?$'      , ReEngageQueueHandler),
    (r'/r/(\d+)/?$', ReEngagePostHandler),
]