#!/usr/bin/env python
from apps.sibt.shopify.views     import *

urlpatterns = [

    (r'/s/shopify',             ShowWelcomePage),
    (r'/s/shopify/code',        ShowCodePage),
    (r'/s/shopify/edit',        ShowEditPage),
    (r'/s/shopify/finished',    ShowFinishedPage),
    (r'/s/sibt.js',             DynamicLoader),
]
