#!/usr/bin/env python

from apps.reengage.shopify.processes import *

urlpatterns = [
    # Views

    # Processes
    (r'/r/shopify/webhook/product/create', CreateReEngageProductShopify),
    (r'/r/shopify/webhook/product/update', UpdateReEngageProductShopify),
    (r'/r/shopify/webhook/product/delete', DeleteReEngageProductShopify),

    (r'/r/shopify/webhook/collections/create', CreateReEngageCollectionsShopify),
    (r'/r/shopify/webhook/collections/update', UpdateReEngageCollectionsShopify),
    (r'/r/shopify/webhook/collections/delete', DeleteReEngageCollectionsShopify),
]