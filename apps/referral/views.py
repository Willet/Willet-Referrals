#!/usr/bin/env python

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc"

import re, urllib
from datetime import datetime, timedelta

from django.utils import simplejson as json
from google.appengine.api import urlfetch, memcache
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app
from time import time

from apps.app.models import * 
from apps.link.models import Link, get_link_by_willt_code
from apps.user.models import get_user_by_cookie, User, get_or_create_user_by_cookie
from apps.client.models import *
from apps.order.models import *
from apps.stats.models import Stats

from util.helpers import *
from util.urihandler import URIHandler
from util.consts import *

class ShowDashboard(URIHandler):
    # Renders a app page
    def get(self, app_id = ''):
        #client          = self.get_client()
        #app_id     = self.request.get( 'id' )
        template_values = {'app' : None}
        
        # Grab the app
        app = get_app_by_id(app_id)
        if app == None:
            self.redirect(url('ShowAccountPage'))
            return
        
        app.compute_analytics('month')
        sms = app.get_reports_since('month', datetime.today() - timedelta(40), count=1)
        template_values['app'] = app
        template_values['sms'] = sms
        total_clicks = app.count_clicks()
        template_values['total_clicks'] = total_clicks
        results, mixpanel = app.get_results( total_clicks )
        
        smap = {'twitter': 0, 'linkedin': 1, 'facebook': 2, 'email': 3}

        totals = {'shares':0, 'reach' : 0, 'clicks': 0, 'conversions': 0, 'profit': 0, 'users': [], 'name':''}
        service_totals = []
        props = ['shares', 'reach', 'clicks', 'conversions', 'profit']
        while len(service_totals) < len(smap):
            service_totals.append({'shares':0, 'reach' : 0, 'clicks': 0, 'conversions': 0, 'profit': 0, 'users': [], 'name':''})
                
        for s in sms:
            row = smap[s['name']]
            service_totals[row]['name'] = s['name']
            service_totals[row]['users'].append(s['users'])
            for prop in props:
                totals[prop] += s[prop]
                service_totals[row][prop] += s[prop]
            
        template_values['results']     = results
        template_values['mixpanel']    = mixpanel
        template_values['has_results'] = len( results ) != 0
        template_values['current'] = 'app'

        template_values['api_key'] = MIXPANEL_API_KEY
        template_values['platform_secret'] = hashlib.md5(MIXPANEL_SECRET + app.uuid).hexdigest()
        template_values['totals'] = totals
        template_values['service_totals'] = service_totals
        template_values['BASE_URL'] = URL
        logging.info(service_totals) 
        
        self.response.out.write(
            self.render_page(
                'app.html', 
                template_values
            )
        )

class ShowJSONPage( URIHandler ):
    # Renders a app page
    def get(self):
        client = self.get_client() # May be None
        app_id = self.request.get( 'id' )
        template_values = { 'app' : None }
        
        if app_id:
            
            # Grab the app
            app = get_app_by_id( app_id )
            if app == None:
                self.redirect( '/account' )
                return
            
            # Gather info to display
            total_clicks = app.count_clicks()
            results, foo = app.get_results( total_clicks )
            has_results  = len(results) != 0
            
            logging.info('results :%s' % results)
            
            # App details
            template_values['app'] = { 'title' : app.title, 
                                            'product_name' : app.product_name,
                                            'target_url' : app.target_url,
                                            'blurb_title' : app.blurb_title,
                                            'blurb_text' : app.blurb_text,
                                            'share_text': app.share_text, 
                                            'webhook_url' : app.webhook_url }
            template_values['total_clicks'] = total_clicks
            template_values['has_results']  = has_results
            
            to_show = []
            for r in results:
                e = {'place' : r['num'],
                     'click_count' : r['clicks'],
                     'clicks_ratio' : r['clicks_ratio']}
                     
                if r['user']:
                    e['twitter_handle'] = r['user'].twitter_handle
                    e['user_uid'] = r['link'].supplied_user_id
                    e['twitter_followers_count'] = r['user'].twitter_followers_count
                    e['klout_score'] = r['user'].kscore
                    
                to_show.append( e )
                
            if has_results:
                template_values['results']  = to_show
        
        self.response.out.write(json.dumps(template_values))

class ShowEditPage( URIHandler ):
    # Renders a app page
    def get(self):
        client       = self.get_client() # may be None
        
        app_id  = self.request.get( 'id' )
        error        = self.request.get( 'error' )
        error_msg    = self.request.get( 'error_msg')
        title        = self.request.get( 'title' )
        product_name = self.request.get( 'product_name' )
        target_url   = self.request.get( 'target_url' )
        blurb_title  = self.request.get( 'blurb_title' )
        blurb_text   = self.request.get( 'blurb_text' )
        share_text   = self.request.get( 'share_text' )
        webhook_url  = self.request.get( 'webhook_url' ) 
        
        template_values = { 'app' : None }
        
        # Fake a app to put data in if there is an error
        
        if error == '1':
            template_values['error'] = 'Invalid url.'
            template_values['app'] = { 'title' : title,
                                            'product_name' : product_name,
                                            'target_url' : target_url,
                                            'blurb_title' : blurb_title,
                                            'blurb_text' : blurb_text,
                                            'share_text' : share_text, 
                                            'webhook_url' : webhook_url }
        elif error == '2':
            template_values['error'] = 'Please don\'t leave anything blank.'
            template_values['app'] = { 'title' : title,
                                            'product_name' : product_name,
                                            'target_url' : target_url,
                                            'blurb_title' : blurb_title,
                                            'blurb_text' : blurb_text,
                                            'share_text' : share_text, 
                                            'webhook_url' : webhook_url }
        elif error == '3':
            template_values['error'] = 'There was an error with one of your inputs: %s' % error_msg
            template_values['app'] = { 'title' : title,
                                            'product_name' : product_name,
                                            'target_url' : target_url,
                                            'blurb_title' : blurb_title,
                                            'blurb_text' : blurb_text,
                                            'share_text' : share_text, 
                                            'webhook_url' : webhook_url }
                                        
        # If there is no app_id, then we are creating a new one:
        elif app_id:
            
            # Updating an existing app here:
            app = get_app_by_id( app_id )
            if app == None:
                self.redirect( '/account' )
                return
            
            template_values['app'] = app
            
        template_values['BASE_URL'] = URL

        self.response.out.write(self.render_page('edit.html', template_values))

class ShowCodePage( URIHandler ):
    # Renders a app page
    @login_required
    def get(self, client):
        app_id = self.request.get( 'id' )
        template_values = { 'app' : None }
        
        if app_id:
            # Updating an existing app here:
            app = get_app_by_id( app_id )
            if app == None:
                self.redirect( '/account' )
                return
            
            if app.client == None:
                app.client = client
                app.put()
                
            template_values['app'] = app
        
        template_values['BASE_URL'] = URL
        
        self.response.out.write(self.render_page('code.html', template_values))

class DoUpdateOrCreate( URIHandler ):
    def post( self ):
        client = self.get_client() # might be None
        
        app_id   = self.request.get( 'uuid' )
        title        = self.request.get( 'title' )
        product_name = self.request.get( 'product_name' )
        target_url   = self.request.get( 'target_url' )
        blurb_title  = self.request.get( 'blurb_title' )
        blurb_text   = self.request.get( 'blurb_text' )
        share_text   = self.request.get( 'share_text' )
        webhook_url  = self.request.get( 'webhook_url' ) 
        
        app = get_app_by_id( app_id )
        
        title = title.capitalize() # caps it!
        
        if title == '' or product_name == '' or target_url == '' or blurb_title == '' or blurb_text == '' or share_text == '' or webhook_url == '':
            self.redirect( '/r/edit?id=%s&error=2&title=%s&blurb_title=%s&blurb_text=%s&share_text=%s&target_url=%s&product_name=%s&webhook_url=%s'
            % (app_id, title, blurb_title, blurb_text, share_text, target_url, product_name, webhook_url) )
            return
            
        if not isGoodURL( target_url ) or not isGoodURL( webhook_url ):
            self.redirect( '/r/edit?id=%s&error=1&title=%s&blurb_title=%s&blurb_text=%s&share_text=%s&target_url=%s&product_name=%s&webhook_url=%s'
            % (app_id, title, blurb_title, blurb_text, share_text, target_url, product_name, webhook_url) )
            return
        
        # If app doesn't exist,
        if app == None:
        
            # Create a new one!
            try:
                uuid = generate_uuid(16)
                app = App( key_name=uuid,
                                     uuid=uuid,
                                     client=client, 
                                     title=title[:100], 
                                     product_name=product_name,
                                     target_url=target_url,
                                     blurb_title=blurb_title,
                                     blurb_text=blurb_text,
                                     share_text=share_text,
                                     webhook_url=webhook_url)
                app.put()
            except BadValueError, e:
                self.redirect( '/r/edit?error=3&error_msg=%s&id=%s&title=%s&blurb_title=%s&blurb_text=%s&share_text=%s&target_url=%s&webhook_url=%s&product_name=%s' % (str(e), app_id, title, blurb_title, blurb_text, share_text, target_url, webhook_url, product_name) )
                return
        
        # Otherwise, update the existing app.
        else:
            try:
                app.update( title=title[:100], 
                                 product_name=product_name,
                                 target_url=target_url,
                                 blurb_title=blurb_title, 
                                 blurb_text=blurb_text,
                                 share_text=share_text, 
                                 webhook_url=webhook_url)
            except BadValueError, e:
                self.redirect( '/r/edit?error=3&error_msg=%s&id=%s&title=%s&blurb_title=%s&blurb_text=%s&share_text=%s&target_url=%s&webhook_url=%s&product_name=%s' % (str(e), app_id, title, blurb_title, blurb_text, share_text, target_url, webhook_url, product_name) )
                return
        
        if client == None:
            self.redirect( '/client/login?u=/r/code?id=%s' % app.uuid )
        else:
            self.redirect( '/r/code?id=%s' % app.uuid )
