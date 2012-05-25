#!/usr/bin/env python

from apps.order.shopify.views import *
from apps.order.shopify.processes import *

urlpatterns = [
    (r'/o/shopify/order.js',            OrderJSLoader),
    (r'/o/shopify/create.js',           CreateShopifyOrder),

    # processes
    (r'/o/shopify/orderNotification',   OrderIframeNotification),
]
