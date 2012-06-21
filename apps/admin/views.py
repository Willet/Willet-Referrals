#!/usr/bin/env python

__author__ = "Willet, Inc."
__copyright__ = "Copyright 2011, Willet, Inc"

import re, urllib, sys
from inspect import getmodule
from datetime import datetime
from time import time

from django.utils import simplejson as json
from google.appengine.api import urlfetch, memcache
from google.appengine.ext import webapp
from google.appengine.api import taskqueue
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

from apps.analytics_backend.models import *
from apps.email.models import Email
from apps.app.models import App
from apps.app.shopify.models import AppShopify
from apps.action.models import Action
# from apps.action.models import ScriptLoadAction
from apps.client.models import Client
from apps.client.shopify.models import ClientShopify
from apps.link.models import Link
from apps.order.shopify.models import OrderShopify
from apps.product.shopify.models import ProductShopify
from apps.sibt.actions import *
from apps.sibt.models import SIBT
from apps.sibt.shopify.models import SIBTShopify
from apps.sibt.models import SIBTInstance
from apps.user.models import *
from util import httplib2
from util.consts import *
from util.helpers import *
from util.helpers import url as reverse_url
from util.urihandler import URIHandler
from util.memcache_bucket_config import MemcacheBucketConfig


class ShowRoutes(URIHandler):
    def format_route(self, route):
        memcache.set('reload_uris', True)

        url = route[0]
        obj = route[1]
        obj_name = obj.__name__
        obj_doc = getattr(obj, '__doc__', '') or ''
        module = getmodule(obj).__name__
        return {
            'route': url,
            'obj': obj_name,
            'module': module,
            'doc': obj_doc,
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
                logging.warn('error importing %s: %s' % (app, e), exc_info=True)

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
    """Shows all App objects in the datastore.

    Some modifying features are available.
    """
    def get_app_list(self):
        all_apps = App.all()
        apps = {}
        for app in all_apps:
            try:
                d = {
                    'uuid': app.uuid,
                    'client_name': app.client.name if app.client else '',
                    'class_name': app.class_name(),
                    'client': getattr (app, 'client'),
                    'app': app
                }
                if not d['class_name'] in apps:
                    apps[d['class_name']] = []

                apps[d['class_name']].append(d)
            except Exception,e:
                logging.warn('Error adding app: %s' % e, exc_info=True)
        return apps

    #@admin_required
    def get(self, client=None):
        template_values = {
            'apps': self.get_app_list()
        }

        self.response.out.write(self.render_page(
                'manage_apps.html',
                template_values
            )
        )

    #@admin_required
    def post(self, admin=None):
        """ does a predefined list of actions on apps."""
        app_id = self.request.get('app_id')
        action = self.request.get('action')
        app = App.get(app_id)

        messages = []

        if app != None:
            # we got an app
            logging.info('running action %s on app of type %s\nbutton: %s\ntb: %s' % (
                action,
                app.class_name(),
                app.button_enabled,
                app.top_bar_enabled
            ))
            if app.class_name() == 'SIBTShopify':
                if action == 'enable_button':
                    app.button_enabled = True
                    app.put()
                elif action == 'disable_button':
                    app.button_enabled = False
                    app.put()
                elif action == 'enable_tb':
                    app.top_bar_enabled = True
                    app.put()
                elif action == 'disable_tb':
                    app.top_bar_enabled = False
                    app.put()
                elif action == 'set_number_shows_before_tb':
                    app.num_shows_before_tb = int(self.request.get('num_shows_before_tb'))
                    app.put()
                elif action == 'set_style':
                    app.button_css = self.request.get('button_css')
                    memcache.get('app-%s-sibt-css' % app.uuid) # found in sibt/models.py
                    app.put()
                elif action == 'reset_style':
                    app.button_css = None
                    app.put()
                else:
                    logging.warn("bad action: %s" % action)
                messages.append({
                    'type': 'message',
                    'text': '%s for %s' % (action, app.client.name)
                })
                logging.info('done action %s on app of type %s\nbutton: %s\ntb: %s' % (
                    action,
                    app.class_name(),
                    app.button_enabled,
                    app.top_bar_enabled
                ))
            else:
                messages.append({
                    'type': 'error',
                    'text': 'Invalid class name: %s' % app.class_name()
                })
        else:
            messages.append({
                'type': 'error',
                'text': 'Could not get app for id: %s' % app_id
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


class ShowActions(URIHandler):
    #@admin_required
    #def get(self, admin):
    def get(self):
        template_values = {}

        self.response.out.write(self.render_page(
                'actions.html',
                template_values,
            )
        )


class GetActionsSince(URIHandler):
    #@admin_required
    #def get(self, admin):
    def get(self):
        """This is going to fetch actions since a datetime"""
        since = self.request.get('since')
        before = self.request.get('before')
        try:
            actions = Action.all()
            actions = actions.order('-created')
            if since:
                logging.info('filtering by since %s' % since)
                last_pull = Action.get(str(since))
                actions = actions.filter('created >', last_pull.created)
                actions = sorted(actions, key=lambda action: action.created)
            elif before:
                logging.info('filtering actions before %s' % before)
                before_pull = Action.get(str(before))
                actions = actions.filter('created <', before_pull.created)
                actions = actions.fetch(limit=10)
                #actions = sorted(actions, key=lambda action: action.created)
            else:
                actions = actions.order('created').fetch(limit=10)
                logging.info('%s' % actions)
                actions = sorted(actions, key=lambda action: action.created)
                logging.info('%s' % actions)

            actions_json = []
            for action in actions:
                # add some extra shit
                user = to_dict(action.user)
                user['name'] = action.user.name

                client = action.app_.client
                client = to_dict(client)

                created_format = '%s' % action.created
                action = to_dict(action)
                action['created_format'] = created_format


                actions_json.append({
                    'action': action,
                    'user': user,
                    'client': client
                })
            actions_json = json.dumps(actions_json)

            self.response.out.write(actions_json)

        except Exception, e:
            logging.error(e, exc_info=True)
            self.response.out.write(e)


class FBConnectStats(URIHandler):
    def get(self):
        no_connect = SIBTNoConnectFBDialog.all().count()
        connect = SIBTConnectFBDialog.all().count()

        instance_connect = SIBTInstanceCreated.all().filter('medium =', "ConnectFB").count()
        instance_noconnect = SIBTInstanceCreated.all().filter('medium =', "NoConnectFB").count()

        html = "<h2> Opportunity Counts </h2>"
        html += "<p>No Connect Dialog: %d</p>" % no_connect
        html += "<p>Connect Dialog: %d</p>" % connect

        html += "<h2> Instances </h2>"
        html += "<p>No Connect Dialog: %d</p>" % instance_noconnect
        html += "<p>Connect Dialog: %d</p>" % instance_connect

        self.response.out.write(html)


class ReloadURIS(URIHandler):
    def get(self):
        if self.request.get('all'):
            flushed = memcache.flush_all()
            message = 'Flush all: %s' % flushed
        else:
            memcache.set('reload_uris', True)
            message = 'reload_uris = True'
        template_values = {
            'message': message,
            'stats': memcache.get_stats()
        }
        self.response.out.write(self.render_page('reload_uris.html',
            template_values))


class CheckMBC(URIHandler):
    """ /admin/check_mbc displays the current number of "memcache buckets".
        /admin/check_mbc?num=50 sets the number of memcache buckets to 50.
        Default seems to be 20 or 25. """
    #@admin_required
    #def get(self, admin):
    def get(self):
        mbc = MemcacheBucketConfig.get_or_create('_willet_actions_bucket')
        num = self.request.get('num')
        if num:
            mbc.count = int(num)
            mbc.put()

        self.response.out.write('Count: %d' % mbc.count)


class ShowMemcacheConsole(URIHandler):
    #@admin_required
    #def post(self, admin):
    def post(self):
        key = self.request.get('key')
        value = None
        clear_value = self.request.get('clear')
        new_value = self.request.get('value')
        protobuf = self.request.get('protobuf')
        messages = []
        if key:
            logging.info('looking up key: %s' % key)
            value = memcache.get(key)
            if protobuf and value:
                value = db.model_from_protobuf(entity_pb.EntityProto(value))
                value = to_dict(value)
            if clear_value:
                memcache.set(key, '')
                messages.append("Cleared %s"% key)
            if new_value:
                if protobuf:
                    messages.append('Not supported')
                else:
                    memcache.set(key, new_value)
                    messages.append('Changed %s from %s to %s' % (
                        key, value, new_value
                    ))
            logging.info('got value: %s' % value)
        data = {
            'key': key,
            'value': value,
            'new_value': new_value,
            'messages': messages,
        }
        self.response.headers['Content-Type'] = "application/json"
        self.response.out.write(json.dumps(data))

    #@admin_required
    #def get(self, admin):
    def get(self):
        self.response.out.write(self.render_page(
                'memcache_console.html', {},
            )
        )


class ShowCounts(URIHandler):
    def get(self):

        btn_shows = SIBTShowingButton.all().count()

        click_ask_btn = SIBTUserClickedButtonAsk.all().count()
        click_ask_overlay = SIBTUserClickedOverlayAsk.all().count()
        click_ask_bar = SIBTUserClickedTopBarAsk.all().count()

        ask_shows = SIBTShowingAskIframe.all().count()

        ask_share = SIBTAskUserClickedShare.all().count()

        connect_cancelled = SIBTFBConnectCancelled.all().count()

        str = "<p>Button Shows: %d</p>" % btn_shows

        str += "<p>Btn Clicks: %d</p>" % click_ask_btn
        str += "<p>Bar Clicks: %d</p>" % click_ask_bar
        str += "<p>Overlay Clicks: %d</p>" % click_ask_overlay
        str += "<p>Showing Ask: %d</p>" % ask_shows
        str += "<p>Shared the Ask: %d</p>" % ask_share
        str += "<p>FB Connect Cancelled: %d</p>" % connect_cancelled

        self.response.out.write(str)


class ShowAnalytics(URIHandler):
    #@admin_required
    #def get(self, admin):
    def get(self):

        template_values = {
            'actions': actions_to_count,
            'app': ''
            }
        self.response.out.write(
            self.render_page('analytics.html', template_values)
        )


class ShowAppAnalytics(URIHandler):
    def get(self, app_uuid):
        app = App.get(app_uuid)

        template_values = {
            'actions': actions_to_count,
            'app': app
            }
        self.response.out.write(
            self.render_page('analytics.html', template_values)
        )


class AppAnalyticsCompare(URIHandler):
    #@admin_required
    #def get(self, admin):
    def get(self):
        template_values = {
            'actions': actions_to_count,
            'app': ''
            }
        self.response.out.write(
            self.render_page('analytics.html', template_values)
        )


class EmailEveryone (URIHandler):
    # TODO: change mass_mail_client.html to call EmailBatch instead of post
    # TODO: change EmailBatch request into BatchRequest
    """ Task Queue-based blast email URL. """
    #@admin_required
    #def get (self, admin):
    def get (self):
        # render the mail client
        template_values = {}
        self.response.out.write(self.render_page('mass_mail_client.html', template_values))

    #@admin_required
    #def post (self, admin):
    def post (self):
        batch_size = 100
        full_name = ''

        logging.info("Sending everyone an email.")

        app_cls = self.request.get('app_cls')
        target_version = self.request.get('version')
        subject = self.request.get('subject')
        body = self.request.get('body')

        logging.info('Requested email:\nApp Class = %s\nApp version = %r\nSubject = %s\nBody = %s'
                        % (app_cls, target_version, subject, body))

        # Check that we have something to email
        if not (len(subject) > 0) or not (len(body) > 0):
            self.error(400) # Bad Request
            return

        params = {
            'batch_size':   batch_size,
            'offset':       0,
            'app_cls':      app_cls,
            'subject':      subject,
            'body':         body
        }
        if target_version:
            params.update({ 'target_version': target_version })

        # Initiate batched emailing
        taskqueue.add(url=url('EmailBatch'), params=params)

        self.response.headers['Content-Type'] = 'text/plain'
        self.response.out.write ("%r" % all_emails)
        return


class RealFetch(URIHandler):
    """Can't find what you want? Use RealFetch to scrape the entire DB!"""
    def get(self):
        """In your query string, do ?kind=App
                                    &field1=something
                                    &field2=some_other
        to search for Apps with field1 equal to 'something'
        and field2 equal to 'some_other' at the same time.

        Criteria stack.

        This view costs a lot of reads. Do not use unless you really want to
        confirm something really exists.
        """
        criteria = {}

        self.response.headers['Content-Type'] = 'text/plain'
        try:
            kind = globals()[self.request.get('kind')]
            kind_objs = db.Query(kind)
        except:
            # if kind isn't a Kind, those lines will certainly blow up
            return

        # get {'field1': 'something', ...} for all non-empty values
        for c in self.request.arguments():
            if self.request.get(c):
                criteria[c] = self.request.get(c)
        del(criteria['kind'])

        self.response.out.write ('%r\n' % criteria)

        for obj in kind_objs:
            for criterion in criteria.keys():
                if getattr(obj, criterion, None) != criteria[criterion]:
                    continue  # this item fails
            # this item passes
            self.response.out.write ('[%s] %r\n' % (getattr(obj,'uuid', '???'),
                                                    obj))
