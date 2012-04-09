#!/usr/bin/env python

from apps.product.processes import *

urlpatterns = [
    (r'/product/create', CreateProduct)
]
