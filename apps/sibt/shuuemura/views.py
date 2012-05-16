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
        domain = 'http://shuuemura-usa.com'
        email = 'shuuemura@getwillet.com'  # need to activate this one
        first_name = "Shu Uemura"
        last_name = "USA"  # heheh (his name is actually Uemura Shu)
        phone = "1-888-748-5678"
        vendor = "Shu Uemura USA"  # unique vendor name

        # vendor-agnostic below this line
        logging.info('SIBTShuuemuraWelcome: trying to create app')

        # show the script as plain text (without executing it)
        self.response.headers['Content-Type'] = 'text/plain'

        user = User.get_or_create_by_email(email=email, request_handler=self,
                                           app=None)
        if not user:
            logging.error('wtf, no user?')
            return

        full_name = "%s %s" % (first_name, last_name)
        user.update(email=email,
                    first_name=first_name,
                    last_name=last_name,
                   #name=full_name,  # can't assign to read-only property
                    full_name=full_name,
                    phone=phone,
                    accepts_marketing=False)

        client = Client.get_or_create(url=domain, request_handler=self,
                                      user=user)
        if not client:
            logging.error('wtf, no client?')
            return

        # got a client; update its info
        client.email = email
        client.name = full_name
        client.vendor = vendor
        client.put()

        user.update(client=client)  # can't bundle with previous user update

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
                           'client': client,
                           'sibt_version': app.version,
                           'new_order_code': True}

        # give you (the admin?) the install code
        self.response.out.write(self.render_page('../templates/vendor_include.js',
                                                 template_values))
        return