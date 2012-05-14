#!/usr/bin/env python

__author__ = "Willet, Inc."
__copyright__ = "Copyright 2012, Willet, Inc"

from apps.client.models import Client
from apps.code.models import DiscountCode

from util.helpers import admin_required
from util.urihandler import URIHandler


class ShowClientDiscountCodes(URIHandler):

    @admin_required
    def get(self, admin):
        store_url = self.request.get('store_url',
                                     'http://kiehn-mertz3193.myshopify.com')
        client = Client.get_by_url(store_url)

        '''
        test_code = DiscountCode.create(code='12345',
                                        client=client)
        '''
        for code in client.discount_codes:
            self.response.out.write('%s\n' % code.uuid)