#!/usr/bin/env python

from apps.product.views import *
from apps.product.processes import *

urlpatterns = [
    (r'/product/create', CreateProduct),
    (r'/product/get_reach', FetchProductReach),
    (r'/collection', CollectionJSONDynamicLoader),
    (r'/product', ProductJSONDynamicLoader),
]
