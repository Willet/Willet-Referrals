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

class TrackRemoteError(webapp.RequestHandler):
    def get(self):
        referer = self.request.headers.get('referer')
        ua = self.request.headers.get('user-agent')
        remote_ip = self.request.remote_addr
        error = self.request.get('error')
        script = self.request.get('script')
        stack_trace = self.request.get('st')
        mail.send_mail(
            sender = 'rf.rs error reporting <Barbara@rf.rs>',
            to = 'fraser@getwillet.com',
            subject = 'Javascript callback error',
            body = """We encountered an error
                Page:       %s
                Script:     %s
                User Agent: %s
                Remote IP:  %s
                Error Name: %s
                Error Message:
                %s""" % (
                    referer,
                    script,
                    ua,
                    remote_ip,
                    error,
                    stack_trace
            )
        )
        self.redirect('%s/static/imgs/noimage.png' % URL)

