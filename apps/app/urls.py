#!/usr/bin/env python
from apps.app.views import *
from apps.app.processes import *

urlpatterns = [
    # Views
    #(r'/a/shopify',   ShopifyRedirect),
    (r'/a/deleteApp', DoDeleteApp),

    # Processes
    (r'/a/appClicksCounter',    AppClicksCounter),
]
