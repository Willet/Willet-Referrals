#!/usr/bin/env python

from apps.client.shopify.views import *
from apps.client.shopify.processes import *

urlpatterns = [
    (r'/client/shopify/getProducts', FetchShopifyProducts),
]
