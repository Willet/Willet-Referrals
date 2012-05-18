#!/usr/bin/env python

"""Contains functions to initialise a SIBT app for Shu Uemura."""

__author__ = "Willet, Inc."
__copyright__ = "Copyright 2012, Willet, Inc"

import logging

from apps.sibt.processes import VendorSignUp

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
        # vendor-agnostic below this line
        logging.info('SIBTShuuemuraWelcome: trying to create app')

        domain = 'http://shuuemura-usa.com'
        # email = 'shuuemura@getwillet.com'  # need to activate this one
        email = 'brian@getwillet.com'  # it was said that these emails go to me
        first_name = "Shu Uemura"
        last_name = "USA"  # heheh (his name is actually Uemura Shu)
        phone = "1-888-748-5678"

        # so it doesn't execute the javascript
        self.response.headers['Content-Type'] = 'text/plain'
        (success, script) = VendorSignUp(request_handler=self,
                                         domain=domain,
                                         email=email,
                                         first_name=first_name,
                                         last_name=last_name,
                                         phone=phone)

        self.response.out.write(script)