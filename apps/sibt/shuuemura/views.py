#!/usr/bin/env python

"""Contains functions to initialise a SIBT app for Shu Uemura."""

__author__ = "Willet, Inc."
__copyright__ = "Copyright 2012, Willet, Inc"

import logging

from apps.sibt.models import SIBT
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

        # QA servers: http://qa.shu.inspreview.com, http://staging.shuuemura-usa.com
        domain = self.request.get('domain', 'http://shuuemura-usa.com')

        email = self.request.get('email', 'no-reply@shuuemura-usa.com')

        first_name = self.request.get('first_name', 'Shu Uemura')
        # heheh (his name is actually Uemura Shu)
        last_name = self.request.get('last_name', 'USA')

        phone = self.request.get('phone', '1-888-748-5678')

        # so it doesn't execute the javascript
        self.response.headers['Content-Type'] = 'text/plain'
        (success, script) = VendorSignUp(request_handler=self,
                                         domain=domain,
                                         email=email,
                                         first_name=first_name,
                                         last_name=last_name,
                                         phone=phone,
                                         wosib_enabled=False,
                                         bottom_popup_enabled=False)

        if success:
            app = SIBT.get_by_url(domain)
            if app:  # custom settings
                app.top_bar_enabled = False
                app.bottom_popup_enabled = False
                app.put_later()

        self.response.out.write(script)