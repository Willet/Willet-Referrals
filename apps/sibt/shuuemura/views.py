#!/usr/bin/env python

__author__ = "Willet, Inc."
__copyright__ = "Copyright 2012, Willet, Inc"

import hashlib
import datetime

from apps.client.models import Client
from apps.sibt.models import SIBT
from apps.user.actions import UserCreate
from apps.user.models import User

from util.consts import URL
from util.helpers import url
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

        # def get_or_create(url, request_handler=None, user=None):
        client = Client.get_or_create(url=domain, request_handler=self,
                                      user=user)
        if not client:
            logging.error('wtf, no client?')
            return

        # def get_or_create(client=None, domain=''):
        app = SIBT.get_or_create(client=client, domain=domain)
        if not client:
            logging.error('wtf, no app?')
            return

        # put back the UserAction that we skipped making
        UserCreate.create(user, app)

        template_values = {'app': app,
                           'URL': URL,
                           'shop_name': shop_name,
                           'shop_owner': shop_owner,
                           'client_email': client_email,
                           'client_uuid': client.uuid,
                           'new_order_code': True}
        self.response.out.write(self.render_page('welcome.html',
                                                 template_values))
        return