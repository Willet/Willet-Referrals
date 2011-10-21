#!/usr/bin/env python
from apps.app.shopify.views import *
from apps.app.shopify.processes import *

urlpatterns = [
    (r'/a/shopify',   ShopifyRedirect),
    (r'/a/shopify/deleteApp', DoDeleteApp),
    
    # processes
    (r'/a/shopify/webhook/uninstalled/(.*)/', DoUninstalledApp),
]

