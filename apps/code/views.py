#!/usr/bin/env python

__author__ = "Willet, Inc."
__copyright__ = "Copyright 2012, Willet, Inc"

from apps.client.models import Client
from apps.code.models import DiscountCode

from util.helpers import admin_required
from util.urihandler import URIHandler


class ShowClientDiscountCodes(URIHandler):
    """Admin interface for showing all codes for a client."""
    #@admin_required
    #def get(self, admin):
    def get(self):
        """Supply a client using store_url or client_uuid."""
        self.response.headers['Content-Type'] = 'text/plain'
        client = Client.get_by_url(self.request.get('store_url', '')) or \
                 Client.get(self.request.get('client_uuid', ''))

        if not client:
            self.response.out.write('No client specified\n')
            return

        for code in client.discount_codes:
            self.response.out.write('%s\n' % code.uuid)

class DispenseClientDiscountCode(URIHandler):
    """Writes out a discount code for a given client. The code will
    then be marked as 'used'. Note that 'used' is not the same as 'rebated';
    used means being given out, while rebated means that the user has redeemed
    the coupon.

    [!] There is nothing stopping malicious users from
        getting unlimited discount codes through this control.
    """
    def get(self):
        self.response.headers['Content-Type'] = 'text/plain'
        client = Client.get_by_url(self.request.get('store_url', '')) or \
                 Client.get(self.request.get('client_uuid', ''))

        if not client:
            logging.error('No client specified')
            return

        code = DiscountCode.get_by_client_at_random(client)
        self.response.out.write(code.code)  # here is the code.
            return