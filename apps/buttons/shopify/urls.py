#!/usr/bin/env python
from apps.buttons.processes import *
from apps.buttons.views import *

urlpatterns = [
    (r'/b/shopify/load/(.*)', DynamicLoader),
    (r'/b/shopify/edit/(.*)/ajax/', EditButtonAjax),
    (r'/b/shopify/edit/(.*)/', EditButton),
    (r'/b/shopify/', ListButtons),
]

