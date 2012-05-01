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
from apps.action.models import ScriptLoadAction
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


class Admin(URIHandler):
    @admin_required
    def get(self, admin):
        links = Link.all()
        str = " Bad Links "
        for l in links:
            clicks = l.count_clicks()
            if l.user == None and clicks != 0:
                str += "<p> URL: %s Clicks: %d Code: %s Campaign: %s Time: %s</p>" % (l.target_url, clicks, l.willt_url_code, l.campaign.title, l.creation_time)

        self.response.out.write(str)


class ShowRoutes(URIHandler):
    def format_route(self, route):
        memcache.set('reload_uris', True)

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


class SIBTInstanceStats(URIHandler):
    def no_code(self):
        str += "<h1> Live Instances </h1>"
        live_instances = SIBTInstance.all().filter('is_live =', True)
        for l in live_instances:
            try:
                if not l.asker.is_admin():
                    str += "<p> <a href='%s/admin/sibt?w=%s'> Store: %s Link: %s </a></p>" % (URL, l.link.get_willt_code(), l.app_.store_name, l.link.get_willt_code)
            except:
                pass

        str += "<br /><br /><h1> Dead Instances </h1>"
        dead_instances = SIBTInstance.all().filter('is_live =', False)
        for l in dead_instances:
            try:
                if not l.asker.is_admin():
                    str += "<p> <a href='%s/admin/sibt?w=%s'> Store: %s Link: %s </a></p>" % (URL, l.link.willt_url_code, l.app_.store_name, l.link.willt_url_code)
            except:
                pass
        return str


    def get(self):
        willt_code = self.request.get('w')

        if willt_code == '':
            self.response.out.write(self.no_code())
            return

        link = Link.get_by_code(willt_code)

        instance = link.sibt_instance.get()
        asker = instance.asker

        # Get all actions
        actions = Action.all().filter('sibt_instance =', instance)
        clicks = SIBTClickAction.get_by_instance(instance)
        votes = SIBTVoteAction.get_by_instance(instance)

        # Init the page
        str = "<h1>SIBT Instance: "
        str +="<a href='%s'>Link to Vote</a> </h1> " % (link.get_willt_url())

        str += "Started: %s" % instance.created.strftime('%H:%M:%S %A %B %d, %Y')

        str += "<h2># Actions: %d " % actions.count() if actions else 0
        str += "# Clicks: %d " % clicks.count() if clicks else 0
        str += "# Votes: %d</h2>" % votes.count() if votes else 0

        str += "<p>Product: <a href='%s'>%s</a></p>" % (link.target_url, link.target_url)
        str += "<p>Asker: '%s' <a href='https://graph.facebook.com/%s?access_token=%s'>FB Profile</a>" % (asker.get_full_name(), asker.fb_identity, asker.fb_access_token)

        str += "<br /><br />"
        str += "<table width='100%'><tr><td width='15%'> Time </td> <td width='15%'> Action </td> <td width='50%'> User </td></tr>"

        # Actions
        so = sorted(actions, key=lambda x: x.created, reverse=True)
        for a in so:
            logging.info("actions %s" % a.user)
            u = a.user

            str += "<tr><td>(%s):</td> <td>%s</td> <td>" % (a.created.strftime('%H:%M:%S'), a.__class__.__name__)

            if hasattr(u, 'fb_access_token'):
                str += "<a href='https://graph.facebook.com/%s?access_token=%s'>%s</a>" % (u.fb_identity, u.fb_access_token, u.get_full_name())
            else:
                str += "'%s'" % u.get_full_name()

            if hasattr(u, 'ips'):
                str += " IPs: %s " % u.ips

                str += " Admin? %s</td> </tr>" % u.is_admin()

        str += "</table> <h2> Instance Comments </h2>"

        str += '<div id="fb-root"></div> <script>(function(d, s, id) { var js, fjs = d.getElementsByTagName(s)[0]; if (d.getElementById(id)) {return;} js = d.createElement(s); js.id = id; js.src = "//connect.facebook.net/en_US/all.js#xfbml=1&appId=181838945216160"; fjs.parentNode.insertBefore(js, fjs); }(document, "script", "facebook-jssdk"));</script>'

        str += '<div class="fb-comments" data-href="%s?%s" data-num-posts="5" data-width="500"></div>' % (instance.url, instance.uuid)

        self.response.out.write(str)
        return


class ShowActions(URIHandler):
    @admin_required
    def get(self, admin):
        template_values = {}

        self.response.out.write(self.render_page(
                'actions.html',
                template_values,
            )
        )


class GetActionsSince(URIHandler):
    @admin_required
    def get(self, admin):
        """This is going to fetch actions since a datetime"""
        since = self.request.get('since')
        before = self.request.get('before')
        try:
            actions = Action.all()
            actions = actions.order('-created')
            if since:
                logging.info('filtering by since %s' % since)
                last_pull = Action.get(unicode(since))
                actions = actions.filter('created >', last_pull.created)
                actions = sorted(actions, key=lambda action: action.created)
            elif before:
                logging.info('filtering actions before %s' % before)
                before_pull = Action.get(unicode(before))
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


class ShowClickActions(URIHandler):
    @admin_required
    def get(self, admin):
        things = {
            'tb': {
                'action': 'SIBTUserClickedTopBarAsk',
                'show_action': 'SIBTShowingTopBarAsk',
                'l': [],
                'counts': {},
            },
            'b': {
                'action': 'SIBTUserClickedButtonAsk',
                'show_action': 'SIBTShowingButton',
                'l': [],
                'counts': {},
            }
        }
        actions_to_check = [
            'SIBTShowingAskIframe',
            'SIBTAskUserClickedEditMotivation',
            'SIBTAskUserClosedIframe',
            'SIBTAskUserClickedShare',
            'SIBTInstanceCreated',
        ]
        for t in things:
            things[t]['counts'][things[t]['show_action']] = Action\
                    .all(keys_only=True)\
                    .filter('class =', things[t]['show_action'])\
                    .count(999999)

            for click in Action.all().filter('what =', things[t]['action']).order('created'):
                try:
                    # we want to get the askiframe event
                    # but we have to make sure there wasn't ANOTHER click after this

                    next_show_button = Action.all()\
                            .filter('user =', click.user)\
                            .filter('created >', click.created)\
                            .filter('app_ =', click.app_)\
                            .filter('class =', 'SIBTShowingButton')\
                            .get()

                    for action in actions_to_check:
                        if action not in things[t]['counts']:
                            things[t]['counts'][action] = 0

                        a = Action.all()\
                                .filter('user =', click.user)\
                                .filter('created >', click.created)\
                                .filter('app_ =', click.app_)\
                                .filter('class =', action)\
                                .get()
                        if a:
                            logging.info(a)
                            if next_show_button:
                                if a.created > next_show_button.created:
                                    logging.info('ignoring %s over %s' % (
                                        a,
                                        next_show_button
                                    ))
                                    continue
                            things[t]['counts'][action] += 1
                            logging.info('%s + 1' % action)

                    client = ''
                    if click.app_.client:
                        if hasattr(click.app_.client, 'name'):
                            client = click.app_.client.name
                        elif hasattr(click.app_.client, 'domain'):
                            client = click.app_.client.domain
                        elif hasattr(click.app_.client, 'email'):
                            client = click.app_.client.email
                        else:
                            client = click.app_.client.uuid
                    else:
                        client = 'No client'

                    things[t]['l'].append({
                        'created': '%s' % click.created,
                        'uuid': click.uuid,
                        'user': click.user.name,
                        'client': client
                    })
                except Exception, e:
                    logging.warn('had to ignore one: %s' % e, exc_info=True)
            things[t]['counts'][things[t]['action']] = len(things[t]['l'])

            l = [{'name': item, 'value': things[t]['counts'][item]} for item in things[t]['counts']]
            l = sorted(l, key=lambda item: item['value'], reverse=True)
            things[t]['counts'] = l
        template_values = {
            'tb_counts': things['tb']['counts'],
            'b_counts': things['b']['counts'],
        }

        self.response.out.write(self.render_page('action_stats.html', template_values))


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
    @admin_required
    def get(self, admin):
        mbc = MemcacheBucketConfig.get_or_create('_willet_actions_bucket')
        num = self.request.get('num')
        if num:
            mbc.count = int(num)
            mbc.put()

        self.response.out.write('Count: %d' % mbc.count)


class ShowMemcacheConsole(URIHandler):
    @admin_required
    def post(self, admin):
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

    @admin_required
    def get(self, admin):
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
    @admin_required
    def get(self, admin):

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
    @admin_required
    def get(self, admin):
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
    @admin_required
    def get (self, admin):
        # render the mail client
        template_values = {}
        self.response.out.write(self.render_page('mass_mail_client.html', template_values))

    @admin_required
    def post (self, admin):
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
