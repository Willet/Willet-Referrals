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
    (r'/r/shopify/webhook/orders/create', CreateReEngageOrderShopify),

    (r'/r/shopify/get_or_create_queues', GetOrCreateShopifyQueues),
    (r'/r/shopify/get_or_create_queue', GetOrCreateShopifyQueue),
]
