#!/usr/bin/env python
from apps.buttons.shopify.processes import *
from apps.buttons.shopify.views import *

urlpatterns = [
	# Views
    (r'/b/shopify/beta',        		ButtonsShopifyBeta),
    (r'/b/shopify/',            		ButtonsShopifyBeta),
    (r'/b/shopify',             		ButtonsShopifyBeta),

    (r'/b/shopify/welcome', 			ButtonsShopifyWelcome),
    (r'/b/shopify/upgrade', 			ButtonsShopifyUpgrade),
    (r'/b/shopify/billing_callback', 	ButtonsShopifyBillingCallback),

    (r'/b/shopify/instructions',     	ButtonsShopifyInstructions),

    (r'/b/shopify/error.html',     		ButtonsShopifyInstallError),

    (r'/b/shopify/item_shared',         ButtonsShopifyItemShared)
]

