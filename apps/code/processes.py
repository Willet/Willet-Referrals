#!/usr/bin/env python

__author__ = "Willet, Inc."
__copyright__ = "Copyright 2012, Willet, Inc"

from apps.client.models import Client
from apps.code.models import DiscountCode

from util.helpers import admin_required
from util.urihandler import URIHandler


class ImportDiscountCodes(URIHandler):
    """Lets you add codes manually into the DB."""

    #@admin_required
    #def post(self, admin):
    def post(self):
        """Create a DiscountCode.

        Possible parameters:
        - store_url or client_uuid
        - codes: a CSV of codes being created.
        - used: 1 or 0, denoting whether these codes created have
                already expired.
        - expiry: some kind of date format that python understands,
                  representing the date of "coupon expiry".

        Example call:
        http://brian-willet.appspot.com/code/import
            ?client_uuid=30620aed69b84b38
            &codes=SAVE 40,SAVE 50,SAVE 60,SAVE 70
        """
        self.response.headers['Content-Type'] = 'text/plain'
        client = Client.get_by_url(self.request.get('store_url', '')) or \
                 Client.get(self.request.get('client_uuid', ''))

        if not client:
            self.response.out.write('No client specified\n')
            return

        codes = self.request.get('codes', '')
        if not codes:
            self.response.out.write('No codes\n')
            return

        used = bool(self.request.get('used', '0'))

        codes = codes.split(',')
        for code in codes:
            code = code.strip()
            if code:
                try:
                    new_code = DiscountCode.get_or_create(code=code,
                                                          client=client,
                                                          used=used)
                    self.response.out.write('Created code %s\n' % code)
                except:
                    self.response.out.write('Failed to create code\n')


    #@admin_required
    #def get(self, admin):
    def get(self):
        """This should be POST, but then you can't do it from the QS."""
        self.post()

