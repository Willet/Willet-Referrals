#!/usr/bin/env python
from apps.buttons.shopify.processes import *
from apps.buttons.shopify.views import *

urlpatterns = [
    (r'/b/shopify/load/(.*)', ButtonsShopifyJS),
    (r'/b/shopify/edit/(.*)/ajax/', ButtonsShopifyEditAjax),
    (r'/b/shopify/edit/(.*)/', ButtonsShopifyEdit),
    (r'/b/shopify/beta', ButtonsShopifyBeta),
    (r'/b/shopify/', ButtonsShopifyWelcome),
]

