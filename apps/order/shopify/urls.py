#!/usr/bin/env python

from apps.order.shopify.views import *
from apps.order.shopify.processes import *
from util.urihandler import DeprecationHandler

urlpatterns = [
    (r'/o/shopify/order.js',            DeprecationHandler),
    (r'/o/shopify/create.js',           CreateShopifyOrder),

    # processes
    (r'/o/shopify/webhook/create',      OrderWebhookNotification),
    (r'/o/shopify/webhook/create/',     OrderWebhookNotification),
    (r'/o/shopify/orderNotification',   OrderIframeNotification),
]