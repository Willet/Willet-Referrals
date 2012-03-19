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


class BatchRequest(URIHandler):
    """ EXPERIMENTAL: Start a batch request of a class method, which will run
    for every app of app_cls in the db """
    def get(self):
        self.post()

    def post(self):
        """ Expected inputs:
            - batch_size: (int) 0 - 1000
            - offset: (int) database offset
            - app_cls: App class
            - target_version: (Optional)
            - method: method to call on app_cls
            - params: parameters to send to method
        """
        batch_size = self.request.get('batch_size')
        offset = self.request.get('offset')
        app_cls = self.request.get('app_cls')
        target_version = self.request.get('target_version')
        method = self.request.get('method')
        params = json.loads( self.request.get('params'))

        if not batch_size or not (offset >= 0) or not app_cls:
            self.error(400) # Bad Request
            return

        apps = db.Query(App).filter('class = ', app_cls).fetch(limit=batch_size, offset=offset)

        if method:
            if method[0] == '_':
                self.error(403) # Access Denied
                return
            elif not hasattr(app_cls, method) or not callable(app_cls[method]):
                self.error(400) # Bad Request

        # If reached batch size, start another batch at the next offset
        if len(apps) == batch_size:
            p = {
                'batch_size':       batch_size,
                'offset':           offset + batch,
                'app_cls':          app_cls,
                'target_version':   target_version,
                'method':           method,
                'params':           self.request.get('params')
            }
            taskqueue.add(url=url('BatchRequest'), params=p)

        # For each app, try to create an email & send it
        for app in all_apps:
            try:
                # Check version
                if target_version >= 0 and app.version != target_version:
                    # Wrong version, skip this one
                    continue
                app[method]()


class UploadEmailsToMailChimp(URIHandler):
    """ One-time use to upload existing ShopConnection customers to MailChimp """
    def get(self):
        pass

    def post(self):
        pass


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

