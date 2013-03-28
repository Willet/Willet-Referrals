#!/usr/bin/env python

from util.urihandler import DeprecationHandler

urlpatterns = [
    (r'/s/shopify',                 DeprecationHandler),
    (r'/s/shopify/beta',            DeprecationHandler),
    (r'/s/shopify/code',            DeprecationHandler),
    (r'/s/shopify/edit',            DeprecationHandler),
    (r'/s/shopify/(.*)/edit',       DeprecationHandler),
    (r'/s/shopify/finished',        DeprecationHandler),
    (r'/s/shopify/sibt.js',         DeprecationHandler),
    (r'/s/shopify/sibt-ab.js',      DeprecationHandler),
    (r'/s/shopify/error.html',      DeprecationHandler)
]