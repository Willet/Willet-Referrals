#!/usr/bin/env python

"""Code procedures; updates DB codes."""

__author__ = "Willet, Inc."
__copyright__ = "Copyright 2012, Willet, Inc"

import logging

from apps.client.models import Client
from apps.code.models import DiscountCode
from apps.user.models import User

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

        used = bool(self.request.get('used', False))

        codes = codes.split(',')
        for code in codes:
            code = code.strip()
            if code:
                try:
                    new_code = DiscountCode.get_or_create(code=code,
                                                          client=client,
                                                          used=used,
                                                          user=None)
                    self.response.out.write('Created code %s\n' % code)
                except Exception, err:
                    self.response.out.write('Failed to create code: %s\n' % err)

    #@admin_required
    #def get(self, admin):
    def get(self):
        """This should be POST, but then you can't do it from the QS."""
        self.post()


class DispenseClientDiscountCode(URIHandler):
    """Writes out a discount code for a given client. The code will
    then be marked as 'used'. Note that 'used' is not the same as 'rebated';
    used means being given out, while rebated means that the user has redeemed
    the coupon.

    [!] There is nothing stopping malicious users from
        getting unlimited discount codes through this control.

    Prints a code on success, or nothing on error.
    """
    def post(self):
        """Dispense a DiscountCode.

        Possible parameters:
        - store_url or client_uuid
        - email: an email address with which to retrieve a user.
                 it is used only if there is no user cookie.
        """
        le_code = 'All codes have been taken'

        self.response.headers['Content-Type'] = 'text/plain'
        client = Client.get_by_url(self.request.get('store_url')) or \
                 Client.get(self.request.get('client_uuid', ''))
        if not client:
            logging.error('No client specified')
            return

        '''
        app = App.get_by_url(self.request.get('store_url', '')) or \
              App.get(self.request.get('client_uuid', ''))
        '''

        # attempt to find user to reward
        user = User.get_by_cookie(self) or \
               User.get_by_email(self.request.get('email'))
        if not user:
            logging.error('No user could be found by cookie or email')
            return

        if user.user_discount_codes:  # if this user already has one
            logging.warn('User already got a discount code... '
                         'dispensing that one')
            try:
                le_code = user.user_discount_codes[0].code
            except IndexError:
                pass  # failed because code is gone / not created yet

        if not le_code:
            code = DiscountCode.get_by_client_at_random(client)
            if code:
                # now it's marked and we can't use it again
                code.use_code(user=user)
                le_code = code.code

        logging.debug('DISPENSING DISCOUNT CODE %s' % le_code)
        self.response.out.write(le_code)  # here is the code.
        return

    def get(self):
        """Testing or otherwise, it allows for GETting a code."""
        self.post()