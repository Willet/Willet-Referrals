#!/usr/bin/env python

"""Idempotent Code operations go here."""

__author__ = "Willet, Inc."
__copyright__ = "Copyright 2012, Willet, Inc"

import logging

from apps.client.models import Client

from util.urihandler import URIHandler


class ShowClientDiscountCodes(URIHandler):
    """Admin interface for showing all codes for a client."""
    #@admin_required
    #def get(self, admin):
    def get(self):
        """Supply a client using store_url or client_uuid."""
        self.response.headers['Content-Type'] = 'text/plain'
        client = Client.get_by_url(self.request.get('store_url')) or \
                 Client.get(self.request.get('client_uuid'))

        if not client:
            logging.warn('Could not fetch DiscountCodes without client')
            self.response.out.write('No client specified\n')
            return

        for code in client.discount_codes:
            self.response.out.write('%s\n' % code.uuid)