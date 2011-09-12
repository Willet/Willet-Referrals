#!/usr/bin/python

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc."

import hashlib, re, datetime

from django.utils import simplejson as json
from gaesessions import get_current_session
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api.datastore_errors import BadValueError

from apps.stats.models import Stats

from util.helpers    import *
from util.urihandler import URIHandler
from util.consts     import *

class ShowLandingPage( URIHandler ):
    # Renders the main template
    def get(self, page):
        stats = Stats.all().get()
        
        template_values = { 'campaign_results' : stats.landing if stats else '' }
        
        self.response.out.write(self.render_page('landing.html', template_values))

class ShowAboutPage( URIHandler ):
    # Renders the main template
    def get(self):
        thx = self.request.get('thx')
        
        template_values = { 'thanks' : True if thx == '1' else False }
        
        self.response.out.write(self.render_page('about.html', template_values))

class ShowContactPage( URIHandler ):
    # Renders the main template
    def get(self):
        template_values = []
        
        self.response.out.write(self.render_page('contact.html', template_values))

class ShowLoginPage( URIHandler ):
    # Renders the login page
    def get(self):
        session    = get_current_session()
        session.regenerate_id()
        user_email = session.get('email', '');
        url        = self.request.get( 'u' )
        client     = self.get_client()
        
        logging.info("URL : %s EMAIL: %s" % (url, user_email) )
        
        if len(user_email) > 0 and client:
            previousAuthErrors = session.get('auth-errors', False)
            previousRegErrors  = session.get('reg-errors', False)
            
            # we authenticated so clear error cache
            if previousAuthErrors or previousRegErrors:
                session['auth-errors'] = []
                session['reg-errors']  = [] 
                
            self.redirect( url if url else '/account' )
        
        else:
            stats      = Stats.all().get()
            registered = self.request.cookies.get('willt-registered', False)
            clientEmail = session.get('correctEmail', '')
            authErrors = session.get('auth-errors', [])
            regErrors  = session.get('reg-errors', [])
            
            template_values = {  'email': clientEmail,
                                 'authErrors': authErrors,
                                 'regErrors': regErrors,
                                 'loggedIn': False,
                                 'registered': str(registered).lower(),
                                 'url' : url,
                                 'stats' : stats,
                                 'total_users' : stats.total_clients + stats.total_users if stats else 'Unavailable' }
                                 
            self.response.out.write(self.render_page('login.html', template_values))

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


