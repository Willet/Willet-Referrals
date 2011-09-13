#!/usr/bin/python

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc."

import hashlib, re, datetime, sys

import inspect

from django.utils import simplejson as json
from google.appengine.ext import webapp
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
        stats = Stats.all().get()
        landing = ''
        if stats:
            if hasattr(stats, 'landing'):
                landing = stats.landing

        template_values = { 'campaign_results' : landing }
        
        self.response.out.write(self.render_page('landing.html', template_values, appname='homepage'))

class ShowAboutPage( URIHandler ):
    # Renders the main template
    def get(self):
        thx = self.request.get('thx')
        
        template_values = { 'thanks' : True if thx == '1' else False }
        
        self.response.out.write(self.render_page('about.html', template_values, appname='homepage'))

class ShowContactPage( URIHandler ):
    # Renders the main template
    def get(self):
        template_values = []
        
        self.response.out.write(self.render_page('contact.html', template_values, appname='homepage'))

class ShowDemoSitePage( URIHandler ):
    # Renders the main template
    def get(self, page):
        template_values = {
            'LANDING_CAMPAIGN_UUID' : LANDING_CAMPAIGN_UUID,
            'LANDING_CAMPAIGN_STORE' : LANDING_CAMPAIGN_STORE
        }
        
        if page == '' or page == '/':
            page = 'thanks'
        
        self.response.out.write(self.render_page('demo_site/%s.html' % page, template_values, appname='homepage'))

class ShowDashboardTestPage(URIHandler):
    def get(self):
        template_values = {}
        self.response.out.write(self.render_page('dashboard/backup_base.html', template_values, appname='homepage'))



class DoAddFeedback( URIHandler ):
    def post( self ):
        client = self.get_client()
        msg    = self.request.get('message')
        
        feedback = Feedback( client=client, message=msg )
        feedback.put()
        
        self.redirect( '/about?thx=1' )
