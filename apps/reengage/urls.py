#!/usr/bin/env python
from apps.reengage.processes import *
from apps.reengage.views import *

urlpatterns = [
    # Views
    (r'/reengage/(fb|t)?',      ReEngageControlPanel),
    (r'/reengage/post/(fb|t)?', ReEngage),
    (r'/reengage/product',      ReEngageProduct),
    (r'/reengage/find_tweet',   ReEngageFindTweet),
]