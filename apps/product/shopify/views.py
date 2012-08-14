#!/usr/bin/env python


from apps.product.shopify.models import ProductShopify

from util.urihandler import URIHandler


class SkypeCallTestingService(URIHandler):

    def get(self):
        product = ProductShopify.get_by_url(self.request.get('url', ''))
        if product:
            self.response.out.write('%r' % product.client.get_top_products())
        else:
            self.response.out.write('no product')