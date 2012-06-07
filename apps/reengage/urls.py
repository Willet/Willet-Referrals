#!/usr/bin/env python
from apps.reengage.processes import *
from apps.reengage.views import *

urlpatterns = [
    # Views
    (r'/reengage/(fb|t|p)?',      ReEngageControlPanel),
    (r'/reengage/post/(fb|t|p)?', ReEngage),
    (r'/reengage/product',      ReEngageProduct),
    (r'/reengage/find_tweet',   ReEngageFindTweet),
    (r'/reengage/find_pin',     ReEngageFindPin),
]