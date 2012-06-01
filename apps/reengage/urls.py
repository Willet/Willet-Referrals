#!/usr/bin/env python
from apps.reengage.processes import *
from apps.reengage.views import *

urlpatterns = [
    # Views
    (r'/reengage/?',       ReEngageControlPanel),
    (r'/reengage/post',    ReEngageFacebook),
    (r'/reengage/product', ReEngageProduct),
]