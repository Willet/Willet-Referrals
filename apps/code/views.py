#!/usr/bin/env python

__author__ = "Willet, Inc."
__copyright__ = "Copyright 2012, Willet, Inc"

from apps.client.models import Client
from apps.code.models import DiscountCode

from util.helpers import admin_required
from util.urihandler import URIHandler


class ShowClientDiscountCodes(URIHandler):

    #@admin_required
    #def get(self, admin):
    def get(self):
        self.response.headers['Content-Type'] = 'text/plain'
        store_url = self.request.get('store_url',
                                     'http://kiehn-mertz3193.myshopify.com')
        client = Client.get_by_url(store_url) or \
                 Client.get(self.request.get('client_uuid', ''))

        if not client:
            self.response.out.write('No client specified\n')
            return

        for code in client.discount_codes:
            self.response.out.write('%s\n' % code.uuid)