#!/usr/bin/env python

__author__ = "Willet, Inc."
__copyright__ = "Copyright 2011, Willet, Inc"

import datetime

from datetime import datetime, timedelta
from time import time
from urlparse import urlparse

from google.appengine.api import taskqueue
from google.appengine.api import memcache
from google.appengine.ext import db
from google.appengine.ext.webapp import template

# from apps.action.models import ScriptLoadAction
from apps.app.models import *
from apps.client.models import *
from apps.client.shopify.models import *
from apps.email.models import Email
from apps.gae_bingo.gae_bingo import ab_test
from apps.link.models import Link
from apps.order.models import *
from apps.product.models import Product
from apps.sibt.actions import SIBTClickAction, SIBTShowingButton, SIBTVoteAction
from apps.sibt.models import SIBT, SIBTInstance
from apps.sibt.shopify.models import SIBTShopify
from apps.user.models import User
from apps.wosib.shopify.models import WOSIBShopify

from util.consts import *
from util.helpers import *
from util.helpers import url as build_url
from util.shopify_helpers import get_shopify_url
from util.urihandler import URIHandler

class ShowBetaPage(URIHandler):
    def get(self):
        logging.info(SHOPIFY_APPS)
        logging.info(SHOPIFY_APPS['SIBTShopify'])
        template_values = { 'SHOPIFY_API_KEY' : SHOPIFY_APPS['SIBTShopify']['api_key'] }

        self.response.out.write(self.render_page('beta.html', template_values))

class SIBTShopifyWelcome(URIHandler):
    # "install done" page. actually installs the apps.
    def get(self):
        client_email = ''
        client_url = ''
        shop_name = ''
        shop_owner = ''

        logging.info('SIBTShopifyWelcome: trying to create app')
        try:
            client = self.get_client() # May be None if not authenticated

            token = self.request.get('t') # token

            # update client token (needed when reinstalling)
            if client and client.token != token:
                logging.warn('Tokens mismatch! Client probably installed '
                             'two or more of our apps. Updating token.')
                client.token = token
                client.put()

            if not client:
                # client was just put, expected to be in memcache
                logging.error('Memcache is lagging!')
                raise IOError('The server is busy. '
                              'Please refresh the page to try again!')

            client_url = client.url
            app = SIBTShopify.get_or_create(client, token=token) # calls do_install()

            shop_owner = 'Shopify Merchant'
            shop_name = 'Your Shopify Store'
            if client.merchant:
                client_email = client.email
                shop_owner = client.merchant.name or 'Merchant'
                shop_name = client.name

                # Query the Shopify API to update all Products
                taskqueue.add(
                    url = build_url('FetchShopifyProducts'),
                    params = {
                        'client_uuid': client.uuid,
                        'app_type'   : 'SIBTShopify'
                    }
                )

            # Switched to new order tracking code on Jan 16
            if app.created > datetime(2012, 01, 16):
                new_order_code = True
            else:
                new_order_code = False

            template_values = {
                'app': app,
                'URL' : URL,
                'shop_name' : shop_name,
                'shop_owner': shop_owner,
                'client_email': client_email,
                'client_uuid' : client.uuid,
                'new_order_code' : new_order_code
            }
            path = 'welcome.html'

        except Exception, err:
            logging.error('SIBT install error, may require reinstall (%s)' % err,
                          exc_info=True)
            # Email DevTeam
            Email.emailDevTeam('SIBT install error, may require reinstall: %s, %s, %s, %s' %
                               (client_email, shop_owner, client_url, shop_name))
            template_values = {'URL': URL,
                              'reason': err}
            path = 'install_error.html'

        self.response.out.write(self.render_page(path, template_values))
        return

class SIBTShopifyEditStyle(URIHandler):
    """ Modifies SIBT button style - internal use only. """
    @admin_required
    def post(self, app_uuid):
        app = SIBTShopify.get(app_uuid)
        post_vars = self.request.arguments()

        logging.info('Updating %s with styles: \n%s' % (app.store_url,
                                                      [ '%s { %s }' % (var, self.request.get(var)) for var in post_vars ]))

        if self.request.get('set_to_default'):
            # Reset to default CSS
            logging.debug('reset button')
            app.reset_css()
        else:
            # Update custom CSS with new rules
            css_dict = app.get_css_dict()

            for var in post_vars:
                key = value = None
                try:
                    (key, value) = var.split(':')
                except ValueError:
                    continue

                # Rules stored as "holding-element:specific-element" like "willet_button_v3:others"
                if key and value:

                    # Add key if it doesn't already exist
                    if not key in css_dict:
                        css_dict[key] = {}

                    css_dict[key][value] = self.request.get(var)

            # Save updated CSS
            app.set_css(css_dict)
        self.get(app_uuid)

    @admin_required
    def get(self, app_uuid):
        app = SIBTShopify.get(app_uuid)

        css_dict = app.get_css_dict()
        css_values = app.get_css()
        display_dict = {}
        for key in css_dict:
            # because template has issues with variables that have
            # a dash in them
            new_key = key.replace('-', '_').replace('.','_')
            display_dict[new_key] = css_dict[key]

        logging.warn('css: %s' % css_values)

        template_values = {
            'css': css_values,
            'app': app,
            'message': '',
            'ff_options': [
                'Arial,Helvetica',
            ]
        }
        template_values.update(display_dict)

        self.response.out.write(self.render_page('edit_style.html', template_values))

class ShowFinishedPage(URIHandler):
    def get(self):
        app_id = self.request.get('id')
        pages = {
            'one': 'old',
            'two': 'old',
            'three': 'old',
            'four': 'current'
        }
        # Init the template values with a blank app
        template_values = {
            'pages': pages,
            'app' : None,
            'has_app': False
        }
        app = App.get_by_uuid(app_id)
        if app == None:
            self.redirect('/s/edit')
            return

        template_values['has_app'] = True
        template_values['app'] = app
        template_values['analytics'] = True if app.cached_clicks_count != 0 else False
        template_values['BASE_URL'] = URL

        self.response.out.write(
            self.render_page(
                'finished.html',
                template_values
            )
        )


class ShowEditPage(URIHandler):
    def get(self):
        pass


class ShowCodePage(URIHandler):
    def get(self):
       pass


class SIBTShopifyServeAB (URIHandler):
    """ Serve AB values for SIBTShopifyServeScript in a different JSON request.
        Hopes are that it speeds up button rendering.
    """

    def get(self):
        try:
            app = SIBTShopify.get_by_store_url(get_shopify_url(self.request.get('store_url')))
        except db.KindError:
            app = SIBT.get_by_store_url(get_shopify_url(self.request.get('store_url')))

        jsonp = bool(self.request.get('jsonp', False)) # return json format if jsonp is not set

        if not app: # if we can't get the app, return a file anyway
            cta_button_text = "Need advice? Ask your friends!"
        else:
            user = User.get_or_create_by_cookie(self, app)

            # AB-Test or not depending on if the admin is testing.
            if not user.is_admin():
                if app.incentive_enabled:
                    ab_test_options = [ "Not sure? Let friends vote! Save $5!",
                                        "Earn $5! Ask your friends what they think!",
                                        "Need advice? Ask your friends! Earn $5!",
                                        "Save $5 by getting advice from friends!",
                                        "Not sure? Ask your friends.",
                                      ]
                    cta_button_text = ab_test('sibt_incentive_text',
                                                ab_test_options,
                                                user = user,
                                                app = app)
                else:
                    ab_test_options = [ "Not sure? Start a vote!",
                                        "Not sure? Let friends vote!",
                                        "Need advice? Ask your friends to vote",
                                        "Need advice? Ask your friends!",
                                        "Unsure? Get advice from friends!",
                                        "Unsure? Get your friends to vote!",
                                        ]
                    cta_button_text = ab_test('sibt_button_text6',
                                                ab_test_options,
                                                user = user,
                                                app = app)
            else:
                cta_button_text = "ADMIN: Unsure? Ask your friends!"

        # Finally, render the JS!
        self.response.headers.add_header('P3P', P3P_HEADER)
        if jsonp: # JSONP
            self.response.headers['Content-Type'] = 'text/javascript; charset=utf-8'
            self.response.out.write ('var AB_CTA_text = "%s";' % cta_button_text)
        else: # JSON
            self.response.headers['Content-Type'] = 'application/json'
            self.response.out.write ('{ "AB_CTA_text": "%s" }' % cta_button_text)
        return


class SIBTShopifyProductDetection(URIHandler):
    def get(self):
        """Serves up some high quality javascript that detects if our special
        div is on this page, and if so, loads the real SIBT js"""
        store_url = self.request.get('store_url')

        if store_url: # only render if there is a point of doing so
            app = SIBTShopify.get_by_store_url(store_url)
            user = User.get_or_create_by_cookie(self, app)
            target = get_target_url(self.request.headers.get('REFERER'))

            # Store a script load action.
            if not target: # force a referrer so the ScriptLoad always saves
                # commonly caused by naughty visitors who disables referrer info
                # http://en.wikipedia.org/wiki/Referrer_spoofing
                target = "http://no-referrer.com"

            template_values = {
                'URL' : URL,
                'store_url': store_url,
                'user': user,
                'sibt_button_id': '_willet_shouldIBuyThisButton',
            }
            path = os.path.join('apps/sibt/templates/', 'sibt_product_detection.js')
            self.response.headers.add_header('P3P', P3P_HEADER)
            self.response.headers['Content-Type'] = 'text/javascript; charset=utf-8'
            self.response.out.write(template.render(path, template_values))
        return


class SIBTShopifyInstallError (URIHandler):
    def get (self):
        """ Displays an error page for when the SIBT app fails to install.
            Error emails are not handled by this page.
        """

        template_values = {
            'URL' : URL,
            'reason': self.request.get('reason', None),
        }
        path = os.path.join('apps/sibt/shopify/templates/', 'install_error.html')
        self.response.headers.add_header('P3P', P3P_HEADER)
        self.response.headers['Content-Type'] = 'text/html; charset=utf-8'
        self.response.out.write(template.render(path, template_values))
        return


class SIBTShopifyVersion2To3(URIHandler):
    """ TEMPORARY!!! """
    @admin_required
    def get(self, admin):
        """ Updates all version 2 SIBT apps to version 3 """
        logging.warn('TEMPORARY HANDLER')

        apps = SIBTShopify.all().fetch(limit=500)
        app_stats = {
            'v1': 0,
            'v2': 0,
            'v3': 0
        }
        updated_apps = []

        for app in apps:
            if app.version == '1':
                app_stats['v1'] += 1

            elif app.version == '2':
                app_stats['v2'] += 1
                app.version = '3'
                db.put_async(app)
                updated_apps.append(app)

            elif app.version == '3':
                app_stats['v3'] += 1

            else:
                logging.warn('App has no version: %r' % app)

        # Now update memcache
        for app in updated_apps:
            key = app.get_key()
            if key:
                memcache.set(key, db.model_to_protobuf(app).Encode(), time=MEMCACHE_TIMEOUT)

        self.response.out.write("Updated %i v2 apps. Found %i v1 and %i v3 apps." % (app_stats['v2'], app_stats['v1'], app_stats['v3']))

