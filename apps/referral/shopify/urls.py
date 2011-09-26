#!/usr/bin/env python
from apps.referral.shopify.processes import *
from apps.referral.shopify.views     import *

urlpatterns = [
    (r'/r/shopify',                  ShowWelcomePage),
<<<<<<< HEAD
    (r'/r/shopify/',                 ShowWelcomePage),
=======
    (r'/r/shopify/beta',             ShowBetaPage),
>>>>>>> 97572969fad769279483dc1139d54acd116f4eb8
    (r'/r/shopify/code',             ShowCodePage),
    (r'/r/shopify/edit',             ShowEditPage),
    (r'/r/shopify/doUpdateOrCreate', DoUpdateOrCreate),
    (r'/r/shopify/finished',         ShowFinishedPage),
    (r'/r/shopify/load/(.*)',        DynamicLoader),

    # processes
    (r'/r/shopify/webhook/order',    DoProcessOrder),
    (r'/r/shopify/webhook/uninstalled', DoUninstalledApp),
]
