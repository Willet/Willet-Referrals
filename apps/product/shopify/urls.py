#!/usr/bin/env python

from apps.product.shopify.views     import *
from apps.product.shopify.processes import *

urlpatterns = [
    # Views

    # Processes
    (r'/product/shopify/webhook/create', CreateProductShopify),
    (r'/product/shopify/webhook/update', UpdateProductShopify),
    (r'/product/shopify/webhook/delete', DeleteProductShopify)

]

