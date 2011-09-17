#!/usr/bin/env python

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc"

import re, urllib

from django.utils import simplejson as json
from google.appengine.api import urlfetch, memcache
from google.appengine.ext import webapp
from google.appengine.api import mail, taskqueue
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

from apps.link.models import Link

from util.consts import *
from util.helpers import *
from util.urihandler import URIHandler

class TrackCallbackError(webapp.RequestHandler):
    """Notifies us via email of errors when trying to update our twitter
       graph with data from the @anywhere callback"""

    def post(self):
        payload = self.request.get('payload')
        data    = self.request.get('data')
        msg     = self.request.get('msg')

        mail.send_mail(sender="wil.lt error reporting <Barbara@wil.lt>",
                       to="wil.lt tech support <support@wil.lt>",
                       subject="Javascript /t callback error",
                       body= str(payload) + "\n" + str(data) + "\n" + str(msg))
        
        self.response.out.write("Error emailed")


