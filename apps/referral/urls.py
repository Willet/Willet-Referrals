#!/usr/bin/env python
from apps.referral.processes import *
from apps.referral.views import *

urlpatterns = [
    (r'/shopify/r/code', ShowShopifyCodePage),
    (r'/shopify/r/edit', ShowShopifyEditPage),
    (r'/shopify/doUpdateOrCreateCampaign', DoUpdateOrCreateShopifyCampaign),
    (r'/shopify/load/(.*)', DynamicLoader),

    # processes
    (r'/shopify/webhook/order', DoProcessShopifyOrder),
    (r'/conversion', PostConversion),
]


