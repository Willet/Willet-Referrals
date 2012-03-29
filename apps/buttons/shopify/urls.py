#!/usr/bin/env python
from apps.buttons.shopify.processes import *
from apps.buttons.shopify.views import *

urlpatterns = [
	# Views
    (r'/b/shopify/beta',        		ButtonsShopifyBeta),
    (r'/b/shopify/',            		ButtonsShopifyBeta),
    (r'/b/shopify',             		ButtonsShopifyBeta),
    (r'/b/shopify/welcome',     		ButtonsShopifyWelcome),

	(r'/sb/shopify/beta', 				SmartButtonsShopifyBeta),
	(r'/sb/shopify/', 					SmartButtonsShopifyBeta),
	(r'/sb/shopify', 					SmartButtonsShopifyBeta),
	(r'/sb/shopify/upgrade', 			SmartButtonsShopifyUpgrade),
	(r'/sb/shopify/welcome', 			SmartButtonsShopifyWelcome),
    (r'/sb/shopify/billing_callback', 	SmartButtonsShopifyBillingCallback),
]

