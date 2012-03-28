#!/usr/bin/env python

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2012, Willet, Inc"

from datetime import datetime
import re
import hashlib

from django.utils import simplejson as json
from google.appengine.api import taskqueue
from google.appengine.api.mail import EmailMessage
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.runtime import DeadlineExceededError

from apps.email.models import *
from apps.link.models import Link

from util.consts import *
from util.helpers import url 
from util.helpers import remove_html_tags
from util.strip_html import strip_html
from util.urihandler import URIHandler

class SendEmailAsync(URIHandler):
    def get (self):
        self.post()
    
    def post (self):
        ''' Taskqueue-based email allows pages to be displayed 
            before emails are done sending.
        '''
        
        from_address = self.request.get('from_address')
        to_address = self.request.get('to_address')
        subject = self.request.get('subject')
        body = self.request.get('body')
        to_name = self.request.get('to_name')
        replyto_address = self.request.get('replyto_address')
        
        params = {
            "api_user" : "BarbaraEMac",
            "api_key"  : "w1llet!!",
            "to"       : to_address,
            "subject"  : subject,
            "html"     : body,
            "from"     : info,
            "fromname" : "Willet",
            "bcc"      : fraser
        }
        if to_name:
            params['toname'] = to_name
        if replyto_address:
            params['replyto'] = replyto_address

        if ',' in to_address:
            try:
                e = EmailMessage(
                        sender=from_address, 
                        to=to_address, 
                        subject=subject, 
                        html=body
                        )
                e.send()
            except Exception,e:
                logging.error('Error sending email: %s', e)
        else:
            try:
                result = urlfetch.fetch(
                    url = 'https://sendgrid.com/api/mail.send.json',
                    payload = urllib.urlencode( params ), 
                    method = urlfetch.POST,
                    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
                )
                logging.info (result.content)
            except DeadlineExceededError, e:
                logging.error ("SendGrid was lagging; email was not sent.")
