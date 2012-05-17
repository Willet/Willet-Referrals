#!/usr/bin/env python
from apps.app.shopify.views import *
from apps.app.shopify.processes import *

urlpatterns = [
    (r'/a/shopify',                               ShopifyRedirect),
    (r'/a/shopify/deleteApp',                     DoDeleteApp),
    (r'/a/shopify/ui.js',                         ServeShopifyUI),

    # Processes
    (r'/a/shopify/webhook/uninstalled/(.*)/',     DoUninstalledApp)
]

