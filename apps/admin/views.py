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
from apps.action.models import Action, get_sibt_click_actions_by_instance, get_sibt_vote_actions_by_instance
from apps.referral.models import Referral
from apps.referral.shopify.models import ReferralShopify
from apps.client.models import Client, ClientShopify
from apps.link.models import get_link_by_willt_code
from apps.user.models import User, get_user_by_twitter, get_or_create_user_by_twitter, get_user_by_uuid
from apps.sibt.models import SIBTInstance

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

class ImportPlugin(URIHandler):
    def get(self):
        
        try: 
            from plugin.plugin import * 
            logging.error('plugin')
            logging.error(LinkedInOAuthHandler)
        except:
            logging.error('err', exc_info=True)
        self.response.out.write(self.render_page(
                'routes.html',
                {},
            )
        )

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



class SIBTInstanceStats( URIHandler ):
    def get( self ):
        willt_code = self.request.get( 'w' )

        if willt_code == '':
            str = "<h1> Live Instances </h1>"
            live_instances = SIBTInstance.all().filter( 'is_live =', True )
            for l in live_instances:
                try:
                    if not l.asker.is_admin():
                        str += "<p> <a href='%s/admin/sibt?w=%s'> Store: %s Link: %s </a></p>" % (URL, l.link.get_willt_code(), l.app_.store_name, l.link.get_willt_code )
                except:
                    pass
            
            str += "<br /><br /><h1> Dead Instances </h1>"
            dead_instances = SIBTInstance.all().filter( 'is_live =', False )
            for l in dead_instances:
                try:
                    if not l.asker.is_admin():
                        str += "<p> <a href='%s/admin/sibt?w=%s'> Store: %s Link: %s </a></p>" % (URL, l.link.willt_url_code, l.app_.store_name, l.link.willt_url_code )
                except:
                    pass

            self.response.out.write(str)
            return

        link = get_link_by_willt_code( willt_code )

        instance = link.sibt_instance.get()
        asker    = instance.asker

        # Get all actions
        actions = Action.all().filter( 'sibt_instance =', instance )
        clicks  = get_sibt_click_actions_by_instance( instance )
        votes   = get_sibt_vote_actions_by_instance( instance )
        
        # Init the page
        str = "<h1>SIBT Instance: "
        str +="<a href='%s'>Link to Vote</a> </h1> " % (link.get_willt_url())
        
        str += "Started: %s" % instance.created.strftime('%H:%M:%S %A %B %d, %Y')

        str += "<h2># Actions: %d " % actions.count() if actions else 0
        str += "# Clicks: %d " % clicks.count() if clicks else 0
        str += "# Votes: %d</h2>" % votes.count() if votes else 0

        str += "<p>Product: <a href='%s'>%s</a></p>" % (link.target_url, link.target_url)
        str += "<p>Asker: '%s' <a href='https://graph.facebook.com/%s?access_token=%s'>FB Profile</a>" % (asker.get_full_name(), asker.fb_identity, asker.fb_access_token )
        
        str += "<br /><br />"
        str += "<table width='100%'><tr><td width='15%'> Time </td> <td width='15%'> Action </td> <td width='50%'> User </td></tr>"
        
        # Actions
        so = sorted( actions, key=lambda x: x.created, reverse=True )
        for a in so:
            logging.info("actions %s" % a.user )
            u = a.user

            str += "<tr><td>(%s):</td> <td>%s</td> <td>" % (a.created.strftime('%H:%M:%S'), a.__class__.__name__ )         
            
            if hasattr( u, 'fb_access_token' ):
                str += "<a href='https://graph.facebook.com/%s?access_token=%s'>%s</a>" % (u.fb_identity, u.fb_access_token, u.get_full_name())
            else:
                str += "'%s'" % u.get_full_name()

            if hasattr( u, 'ips' ):
                str += " IPs: %s " % u.ips
            
                str += " Admin? %s</td> </tr>" % u.is_admin()

        str += "</table> <h2> Instance Comments </h2>"

        str += '<div id="fb-root"></div> <script>(function(d, s, id) { var js, fjs = d.getElementsByTagName(s)[0]; if (d.getElementById(id)) {return;} js = d.createElement(s); js.id = id; js.src = "//connect.facebook.net/en_US/all.js#xfbml=1&appId=181838945216160"; fjs.parentNode.insertBefore(js, fjs); }(document, "script", "facebook-jssdk"));</script>'

        str += '<div class="fb-comments" data-href="%s?%s" data-num-posts="5" data-width="500"></div>' % (instance.url, instance.uuid)
        
        self.response.out.write( str )
        return
