#!/usr/bin/env python

from apps.app.models import App
from apps.product.shopify.models import ProductShopifyCollection

from util.urihandler import URIHandler

class SkypeCallTestingService(URIHandler):
    def get(self):
        ProductShopifyCollection.fetch(app=App.get_by_url('http://kiehn-mertz3193.myshopify.com'))