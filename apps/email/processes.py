#!/usr/bin/env python

__author__ = "Willet, Inc."
__copyright__ = "Copyright 2012, Willet, Inc"

import urllib

from google.appengine.api import urlfetch
from google.appengine.api.mail import EmailMessage
from google.appengine.runtime import DeadlineExceededError

from apps.email.models import INFO, FRASER

from util.consts import *
from util.urihandler import URIHandler


class SendEmailAsync(URIHandler):
    def get (self):
        self.post()

    def post (self):
        """ Taskqueue-based email allows pages to be displayed
            before emails are done sending.
        """

        from_address    = self.request.get('from_address')
        to_address      = self.request.get('to_address')
        subject         = self.request.get('subject')
        body            = self.request.get('body')
        to_name         = self.request.get('to_name')
        replyto_address = self.request.get('replyto_address')

        params = {  # all fields must be strings!
            "api_user" : "BarbaraEMac",
            "api_key"  : "w1llet!!",
            "to"       : to_address,
            "subject"  : subject,
            "html"     : body,
            "from"     : INFO,
            "fromname" : "Willet",
            "bcc"      : FRASER
        }
        if to_name:
            params['toname'] = to_name
        if replyto_address:
            params['replyto'] = replyto_address

        # URLLib doesn't like unicode values; it can handle unicode strings,
        # but not unicode strings with code points outside ASCII
        # Normally, we would encode both key and value, but we know that the
        # keys are ok because we created them above.
        params = dict( (key, value.encode('utf-8')) for key, value in params.iteritems() )

        if ',' in params["to"]:
            try:
                email = EmailMessage(sender=params["from"],
                                     to=params["to"],
                                     subject=params["subject"],
                                     html=params["html"])
                email.send()
            except Exception,err:
                logging.error('Error sending email: %s', err, exc_info=True)
        else:
            try:
                result = urlfetch.fetch(
                    url = 'https://sendgrid.com/api/mail.send.json',
                    payload = urllib.urlencode(params),
                    method = urlfetch.POST,
                    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
                )
                logging.info (result.content)
            except DeadlineExceededError:
                logging.error("SendGrid was lagging; email was not sent.")
