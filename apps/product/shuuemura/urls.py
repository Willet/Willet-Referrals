#!/usr/bin/env python

from apps.product.shuuemura.processes import *

urlpatterns = [
    # Processes
    (r'/product/shopify/webhook/create', CreateProductShopify),
    (r'/product/shopify/webhook/update', UpdateProductShopify),
    (r'/product/shopify/webhook/delete', DeleteProductShopify)
]

