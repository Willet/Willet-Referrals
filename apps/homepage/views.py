#!/usr/bin/python

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc."

import hashlib, re, datetime, sys

import inspect

from django.utils import simplejson as json
from google.appengine.ext import webapp
from google.appengine.api import urlfetch, memcache

from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api.datastore_errors import BadValueError

from apps.stats.models import Stats

from util.helpers    import *
from util.urihandler import URIHandler
from util.consts     import *
from util.gaesessions import get_current_session

class ShowLandingPage(URIHandler):
    # Renders the main template
    def get(self, page):
        template_values = { }
        
        self.response.out.write(self.render_page('landing.html', template_values))

class ShowPrivacyPage(URIHandler):
    # Renders the main template
    def get(self):
        memcache.set('reload_uris', True)

        template_values = { }
        
        self.response.out.write(self.render_page('privacy.html', template_values))

class ShowTermsPage(URIHandler):
    # Renders the main template
    def get(self):
        template_values = { }
        
        self.response.out.write(self.render_page('terms.html', template_values))

class ShowShopifyPage(URIHandler):
    # Renders the main template
    def get(self):
        template_values = { }
        
        self.response.out.write(self.render_page('shopify.html', template_values))

class ShowMorePage(URIHandler):
    # Renders the main template
    def get(self):
        template_values = { }
        
        self.response.out.write(self.render_page('more.html', template_values))

class ShowAboutPage( URIHandler ):
    # Renders the main template
    def get(self):
        template_values = { }
        
        self.response.out.write(self.render_page('about.html', template_values))

class ShowContactPage( URIHandler ):
    # Renders the main template
    def get(self):
        template_values = []
        
        self.response.out.write(self.render_page('contact.html', template_values))

class ShowDemoSitePage( URIHandler ):
    # Renders the main template
    def get(self, page):
        template_values = {
            'LANDING_CAMPAIGN_UUID' : LANDING_CAMPAIGN_UUID,
            'LANDING_CAMPAIGN_STORE' : LANDING_CAMPAIGN_STORE
        }
        
        if page == '' or page == '/':
            page = 'thanks'
        
        self.response.out.write(self.render_page('demo_site/%s.html' % page, template_values))

class ShowDashboardTestPage(URIHandler):
    def get(self):
        template_values = {}
        self.response.out.write(self.render_page('dashboard/backup_base.html', template_values))

class ShowBetaPage(URIHandler):
    # Renders the main template
    def get(self):
        template_values = []
        
        self.response.out.write(self.render_page('beta.html', template_values))


