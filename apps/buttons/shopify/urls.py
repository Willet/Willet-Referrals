#!/usr/bin/env python
from apps.buttons.shopify.processes import *
from apps.buttons.shopify.views import *

urlpatterns = [
    # Views
    (r'/b/shopify(/|/beta)?',           ButtonsShopifyBeta),
    (r'/b/shopify/learn',               ButtonsShopifyLearn),
    (r'/b/shopify/welcome',             ButtonsShopifyWelcome),
    (r'/b/shopify/upgrade',             ButtonsShopifyUpgrade),
    (r'/b/shopify/install4u',           ButtonsShopifyInstallService),
    (r'/b/shopify/billing_callback',    ButtonsShopifyBillingCallback),
    (r'/b/shopify/instructions',        ButtonsShopifyInstructions),
    (r'/b/shopify/config',              ButtonsShopifyConfig),
    (r'/b/shopify/error.html',          ButtonsShopifyInstallError),
    (r'/b/shopify/item_shared',         ButtonsShopifyItemShared),

    # Processes
    (r'/b/shopify/start_report',        ButtonsShopifyEmailReports),
    (r'/b/shopify/item_shared_report',  ButtonsShopifyItemSharedReport),
]

