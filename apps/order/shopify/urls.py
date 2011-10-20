#!/usr/bin/env python

from apps.order.shopify.views     import *
from apps.order.shopify.processes import *

urlpatterns = [
    (r'/o/shopify/order.js',            OrderJSLoader),
    
    # processes
    (r'/o/shopify/webhook/create',      OrderWebhookNotification),
    (r'/o/shopify/webhook/create/',     OrderWebhookNotification),
    (r'/o/shopify/orderNotification',   OrderIframeNotification),
]
