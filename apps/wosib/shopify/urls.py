#!/usr/bin/env python
from apps.wosib.shopify.views     import *

urlpatterns = [
    (r'/w/shopify',              WOSIBShopifyWelcome),
    (r'/w/shopify/beta',         WOSIBShowBetaPage),
    (r'/w/shopify/(.*)/edit',    SIBTShopifyEditStyle),
    (r'/w/shopify/finished',     WOSIBShowFinishedPage),
    (r'/w/shopify/button.js',    WOSIBShopifyServeScript),
]
