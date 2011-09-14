#!/usr/bin/env python

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc"

import re, urllib, sys
from inspect import getmodule

from django.utils import simplejson as json
from google.appengine.api import urlfetch, memcache
from google.appengine.ext import webapp
from google.appengine.api import taskqueue
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

from apps.app.models import App
from apps.referral.models import Referral
from apps.referral.shopify.models import ReferralShopify
from apps.client.models import Client, ClientShopify
from apps.link.models import *
from apps.user.models import User, get_user_by_twitter, get_or_create_user_by_twitter, get_user_by_uuid

from util.consts import *
from util.helpers import *
from util.urihandler import URIHandler

class Admin( URIHandler ):
    
    @admin_required
    def get(self, admin):
        """
        links = Link.all()

        for l in links:
            if l.target_url != 'http://www.wil.lt' and l.target_url != "http://www.vidyard.com":
                c = l.count_clicks()

                if c > 0:
                    if l.user:
                        # Tell Mixplanel that we got a click
                        taskqueue.add( queue_name = 'mixpanel', 
                                       url        = '/mixpanel', 
                                       params     = {'event' : 'Clicks', 'num' : c, 'campaign_uuid' : l.campaign.uuid, 'twitter_handle' : l.user.get_attr('twitter_handle')} )

        return
        str = ""
        for c in Client.all():
            e  = c.email
            pw = c.passphrase != None

            others = Client.all().filter( 'email =', e )
            for o in others:
                if o.key() == c.key():
                    continue
                
                if o.campaigns.count() == 0:
                    str += "<p> Deleting %s (%s). %s (%d) is in here.</p>" % (o.email, o.passphrase, e, c.campaigns.count())
                    o.delete()
            for o in clients:
                if o.key() == c.key():
                    continue

                if o.email == e:
                    #for camps in o.campaigns:
                        #str += "<p> Reassigning %s to %s</p>" % (camps.title, c.email)
                        #camps.client = c
                        #camps.put()
                    
                    if o.campaigns.count() == 0:
                        str += "<p> Deleting %s (%s). %s is in here.</p>" % (o.email, o.passphrase, e)
                        #o.delete()
        self.response.out.write( str )
        campaigns = Campaign.all()

        str = ""
        for c in campaigns:
            clicks = c.count_clicks()

            if clicks != 0 and c.client.email != 'z4beth@gmail.com' and c.client.email != 'sy@sayedkhader.com':
                str += "<p> Campaign: '%s' URL: %s Owner: %s Tweets: %d Clicks: %d </p>" % (c.title, c.target_url, c.client.email, c.get_shares_count(), clicks)
        
        self.response.out.write( str )
        """
        links = Link.all()
        str = " Bad Links "
        for l in links:
            clicks = l.count_clicks()
            if l.user == None and clicks != 0:
                str += "<p> URL: %s Clicks: %d Code: %s Campaign: %s Time: %s</p>" % (l.target_url, clicks, l.willt_url_code, l.campaign.title, l.creation_time)

        self.response.out.write( str )


class InitRenameFacebookData(webapp.RequestHandler):
    """Ensure all user models have their facebook properties prefixed exactly
       'fb_' and not 'facebook_' """

    def get(self):

        users = User.all()
        logging.info("Fired")
        for u in [u.uuid for u in users if hasattr(u, 'fb_access_token')\
            or hasattr(u, 'first_name') or hasattr(u, 'gender') or\
            hasattr(u, 'last_name') or hasattr(u, 'verifed')]:
            taskqueue.add(url = '/admin/renamefb',
                          params = {'uuid': u})
        self.response.out.write("update dispatched")

class RenameFacebookData(webapp.RequestHandler):
    """Fetch facebook information about the given user"""

    def post(self):
        rq_vars = get_request_variables(['uuid'], self)
        user = get_user_by_uuid(rq_vars['uuid'])
        if user:
            if hasattr(user, 'facebook_access_token'):
                user.fb_access_token = user.facebook_access_token
                delattr(user, 'facebook_access_token')
            for t in ['first_name', 'last_name', 'name', 'verified', 'gender'\
                , 'email']:
                if hasattr(user, t):
                    setattr(user, 'fb_'+t, getattr(user, t))
                    delattr(user, t)
            for err, correction in [('verifed', 'verified')]:
                if hasattr(user, err):
                    setattr(user, correction, getattr(user, err))
                    delattr(user, err)
            user.save()
            logging.info(user)
            logging.info(user.uuid)

class ShowRoutes(URIHandler):
    def format_route(self, route):
        url = route[0]
        obj = route[1]
        obj_name = obj.__name__
        module = getmodule(obj).__name__
        return {
            'route': url,
            'obj': obj_name,
            'module': module,
        }

    def get(self):
        combined_uris = []
        for app in INSTALLED_APPS:
            try:
                import_str = 'apps.%s.urls' % app
                #__import__(import_str)
                old_len = len(combined_uris)
                __import__(import_str, globals(), locals(), [], -1)
                app_urls = sys.modules[import_str]
                combined_uris.extend(app_urls.urlpatterns)
                new_len = len(combined_uris)

                if old_len + len(app_urls.urlpatterns) > new_len:
                    # we clobbered some urls
                    raise Exception('url route conflict with %s' % app)
            except Exception,e:
                logging.error('error importing %s: %s' % (app, e))

        combined_uris = map(self.format_route, combined_uris)
        template_values = {
            'routes': combined_uris
        }
        self.response.out.write(self.render_page(
                'routes.html',
                template_values,
            )
        )

class ManageApps(URIHandler):
    def get_app_list(self):
        all_apps = App.all()
        apps = []
        for app in all_apps:
            d = {
                'uuid': app.uuid,
                'client_name': app.client.name,
                'class_name': app.class_name()
            }
            apps.append(d)
        return apps
    
    @admin_required
    def get(self, client=None):
        template_values = {
            'apps': self.get_app_list() 
        }
        
        self.response.out.write(self.render_page(
                'manage_apps.html',
                template_values
            )
        )

    @admin_required
    def post(self, admin=None):
        rqv = get_request_variables(['app_id', 'action'], self)
        app = App.all().filter('uuid =', rqv['app_id']).get()
        action = rqv['action']
        
        messages = []

        if app != None:
            # we got an app
            logging.info('running action %s on app of type %s' % (
                action,
                app.class_name()
            ))
            if app.class_name() == 'ReferralShopify':
                # we shall just ignore action for now
                client = app.client
                install_script_tags(app.target_url, client.token)
                messages.append({
                    'type': 'message',
                    'text': 'Ran install_script_tags for %s' % client.name
                })
            else:
                messages.append({
                    'type': 'error',
                    'text': 'Invalid class name: %s' % app.class_name()
                })
        else:
            messages.append({
                'type': 'error',
                'text': 'Could not get app for id: %s' % rqv['app_id'] 
            })

        template_values = {
            'apps': self.get_app_list(), 
            'messages': messages
        }
        
        self.response.out.write(self.render_page(
                'manage_apps.html',
                template_values
            )
        ) 

