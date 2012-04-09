#!/usr/bin/env python
from apps.wosib.shopify.views import *

urlpatterns = [
    (r'/w/shopify/wosib.js',    WOSIBShopifyServeScript),
]
