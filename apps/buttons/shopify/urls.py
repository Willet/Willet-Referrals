#!/usr/bin/env python
from apps.buttons.shopify.processes import *
from apps.buttons.shopify.views import *

urlpatterns = [
    (r'/b/shopify/load/(.*)',   LoadButtonsScript),
    (r'/b/shopify/beta',        ButtonsShopifyBeta),
    (r'/b/shopify/',            ButtonsShopifyBeta),
    (r'/b/shopify',             ButtonsShopifyBeta),
    (r'/b/shopify/welcome',     ButtonsShopifyWelcome),
]

