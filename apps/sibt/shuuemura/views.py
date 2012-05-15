#!/usr/bin/env python

"""Contains functions to initialise a SIBT app for Shu Uemura."""

__author__ = "Willet, Inc."
__copyright__ = "Copyright 2012, Willet, Inc"

import logging

from apps.client.models import Client
from apps.sibt.models import SIBT
from apps.user.actions import UserCreate
from apps.user.models import User

from util.consts import URL
from util.urihandler import URIHandler


class SIBTShuuemuraWelcome(URIHandler):
    """Installs the Shu Uemura User, Client, and SIBT App."""
    def get(self):
        """Installs SIBT for Shu Uemura.

        This view is GET for compatibility with existing code.
        Unlike other *Welcome views, this also creates Clients and Users.

        Please do this in a private browsing window, or you will be cookied
        as a Shu Uemura user for a month.
        """
        logging.info('SIBTShuuemuraWelcome: trying to create app')

        domain = 'http://shuuemura-usa.com'
        email = 'shuuemura@getwillet.com'  # need to activate this one

        # def get_or_create_by_email(cls, email, request_handler, app):
        user = User.get_or_create_by_email(email=email, request_handler=self,
                                           app=None)
        if not user:
            logging.error('wtf, no user?')
            return

        # got a user; update its info
        user.update(first_name="Shu Uemura",
                    last_name="USA",  # heheh (his name is actually Uemura Shu)
                    phone="1-888-748-5678",
                    email=email,
                    accepts_marketing=False)

        # def get_or_create(url, request_handler=None, user=None):
        client = Client.get_or_create(url=domain, request_handler=self,
                                      user=user)
        if not client:
            logging.error('wtf, no client?')
            return

        # got a client; update its info
        client.email = email
        client.name = "Shu Uemura USA"
        client.put()

        # def get_or_create(client=None, domain=''):
        app = SIBT.get_or_create(client=client, domain=domain)
        if not client:
            logging.error('wtf, no app?')
            return

        # put back the UserAction that we skipped making
        UserCreate.create(user, app)

        template_values = {'app': app,
                           'URL': URL,
                           'shop_name': client.name,
                           'shop_owner': client.merchant.name,
                           'client_email': client.email,
                           'client_uuid': client.uuid,
                           'new_order_code': True}
        self.response.out.write(self.render_page('../templates/vendor_include.js',
                                                 template_values))
        return
