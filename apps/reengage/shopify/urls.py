#!/usr/bin/env python

from apps.reengage.shopify.processes import *

urlpatterns = [
    # Views

    # Processes
    (r'/r/shopify/webhook/create', CreateReEngageProductShopify),
    (r'/r/shopify/webhook/update', UpdateReEngageProductShopify),
    (r'/r/shopify/webhook/delete', DeleteReEngageProductShopify),
]