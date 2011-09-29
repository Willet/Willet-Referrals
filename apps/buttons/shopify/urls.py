#!/usr/bin/env python
from apps.buttons.shopify.processes import *
from apps.buttons.shopify.views import *

urlpatterns = [
    (r'/b/shopify/load/(.*)', DynamicLoader),
    (r'/b/shopify/edit/(.*)/ajax/', EditButtonAjax),
    (r'/b/shopify/edit/(.*)/', EditButton),
    (r'/b/shopify/beta', ShowBetaPage),
    (r'/b/shopify/', ShowWelcomePage),
]

