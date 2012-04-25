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

from apps.action.models import ButtonLoadAction, ScriptLoadAction
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
        client_email = shop_owner = shop_name = ''
        logging.info('SIBTShopifyWelcome: trying to create app')
        try:
            client = self.get_client() # May be None if not authenticated

            token = self.request.get('t') # token

            # update client token (needed when reinstalling)
            if client and client.token != token:
                client.token = token
                client.put()

            if not client:
                # client was just put, expected to be in memcache
                logging.error('Memcache is lagging!')

            app = SIBTShopify.get_or_create(client, token=token) # calls do_install()
            app2 = WOSIBShopify.get_or_create(client, token=token) # calls do_install()

            shop_owner = 'Shopify Merchant'
            shop_name = 'Your Shopify Store'
            if client is not None and client.merchant is not None:
                client_email = client.email
                shop_owner = client.merchant.get_attr('full_name')
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
                new_order_code = 1
            else:
                new_order_code = 0

            template_values = {
                'app': app,
                'URL' : URL,
                'shop_name' : shop_name,
                'shop_owner': shop_owner,
                'client_email': client_email,
                'client_uuid' : client.uuid,
                'new_order_code' : new_order_code
            }

            self.response.out.write(self.render_page('welcome.html', template_values))
        except Exception, e:
            logging.error('SIbt install error, may require reinstall', exc_info=True)
            # Email DevTeam
            Email.emailDevTeam(
                'SIBT install error, may require reinstall: %s, %s, %s, %s' %
                    (client_email, shop_owner, client.url, shop_name)
            )
            self.redirect ("%s?reason=%s" % (build_url ('SIBTShopifyInstallError'), e))
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


class SIBTShopifyServeScript(URIHandler):
    """When requested serves a plugin that will contain various functionality
    for sharing information about a purchase just made by one of our clients.
    """
    def get(self):
        """Shows the SIBTShopify real-sibt.js.

        This view is in use, but SIBTServeScript is sometimes preferred over
        it. This will eventually be replaced by SIBTServeScript.
        """
        # declare vars.
        app = None
        app_css = ''
        asker_name = ''
        asker_pic = ''
        event = 'SIBTShowingButton'
        has_results = False
        has_voted = False
        instance = None
        is_asker = False
        is_live = False
        link = None
        page_url = ''
        parts = {}
        product = None
        show_votes = False
        show_top_bar_ask = False
        store_url = get_shopify_url(self.request.get('store_url'))
        template_values = {}
        unsure_multi_view = False
        user = None
        votes_count = 0
        willet_code = self.request.get('willt_code')

        page_url = get_shopify_url(self.request.get('url')) or \
                   get_shopify_url(self.request.get('page_url')) or \
                   get_shopify_url(self.request.headers.get('referer', ''))
        page_url = page_url.split('#')[0]  # clean up window.location
        if not page_url:
            # serve comment instead of status code (let customers see it)
            self.response.out.write('/* missing URL */')
            return

        # have page_url
        # store_url: the domain name with which the shopify store registered
        if not store_url:
            # try to get store_url from page_url
            logging.warn("no store_url; attempting to get from page_url")
            parts = urlparse(page_url)
            if parts.scheme and parts.netloc:
                store_url = '%s://%s' % (parts.scheme, parts.netloc)

        if not store_url:
            logging.error("no store_url; quitting")
            self.response.out.write('/* no store_url. specify it! */')
            return

        # have page_url, store_url
        app = SIBTShopify.get_by_store_url(store_url)
        client = Client.get_by_url(store_url)

        # resolve app/client if either of them is not present
        if app and not client:
            client = app.client
        elif client and not app:
            # try to get existing SIBT/SIBTShopify from this client.
            # if not found, create one.
            # we can create one here because this implies the client had
            # never uninstsalled our app.
            app = SIBT.get_or_create(client=client, domain=store_url)

        if not app and not client:
            # neither app not client: we have no business with you
            self.response.out.write('/* no account for %s! '
                                    'Go to http://rf.rs to get an account. */' % store_url)
            return
        logging.info('using %r and %r as app and client.' % (app, client))

        # have page_url, store_url, client, app
        if not hasattr(app, 'extra_url'):
            """Check if page_url (almost always window.location.href) has the
               same domain as store URL.

            Example: http://social-referral.appspot.com/s/shopify/real-s...
            ibt.js?store_url=thegoodhousewife.myshopify.com&willt_code=&...
            page_url=http://thegoodhousewife.co.nz/products/snuggle-blanket

            Note: if a site has multiple extra URLs, only the last used
            extra URL will be available to our system.
            """
            try:
                # is "abc.myshopify.com" part of the store URL, i.e.
                # "http://abc.myshopify.com"?
                if store_url not in app.store_url:
                    # save the alternative URL so it can be called back later.
                    app.extra_url = store_url
                    logging.info ("[SIBT] associating a new URL, %s, "
                                  "with the original, %s" % (app.extra_url,
                                                             app.store_url))
                    app.put()
            except:
                pass  # can't decode page_url as URL; oh well!

        user = User.get_or_create_by_cookie(self, app)
        product = Product.get_or_fetch(page_url, client)

        # have page_url, store_url, client, app, user, and maybe product
        instance = SIBTInstance.get_by_asker_for_url(user, page_url)
        if instance:
            event = 'SIBTShowingResults'
            logging.debug('got instance by user/page_url: %s' % instance.uuid)
        elif willet_code:
            link = Link.get_by_code(willet_code)
            if link:
                instance = link.sibt_instance.get()

        if instance:
            event = 'SIBTShowingResults'
            logging.debug('got instance by willet_code: %s' % instance.uuid)
        elif user:
            instances = SIBTInstance.all(keys_only=True)\
                                    .filter('url =', page_url)\
                                    .fetch(100)
            key_list = [key.id_or_name() for key in instances]
            action = SIBTClickAction.get_for_instance(app, user, page_url, key_list)
            if action:
                instance = action.sibt_instance

        if instance:
            logging.debug('got instance by action: %s' % instance.uuid)
            event = 'SIBTShowingVote'
        else:
            logging.debug('no instance available')

        # If we have an instance, figure out if
        # a) Is User asker?
        # b) Has this User voted?
        if instance and user:
            is_live = instance.is_live
            event = 'SIBTShowingResults'

            # get the asker's first name.
            asker_name = instance.asker.get_first_name() or "Your friend"
            try:
                asker_name = asker_name.split(' ')[0]
            except:
                pass
            if not asker_name:
                asker_name = 'I' # "should asker_name buy this?"

            asker_pic = instance.asker.get_attr('pic') or ''
            votes_count = bool(instance.get_yesses_count() +
                               instance.get_nos_count()) or 0
            is_asker = bool(instance.asker.key() == user.key())
            if not is_asker:
                logging.debug('not asker, check for vote ...')
                vote_action = SIBTVoteAction.get_by_app_and_instance_and_user(app, instance, user)
                has_voted = bool(vote_action)

            # determine whether to show the results button.
            # code below makes button show only if vote was started less than 1 day ago.
            if votes_count:
                time_diff = datetime.now() - instance.created
                logging.debug ("time_diff = %s" % time_diff)
                if time_diff <= timedelta(days=1):
                    has_results = True
            logging.debug ("has_results = %s" % has_results)

        # unsure detection
        if app and user and not instance:
            tracked_urls = SIBTShowingButton.get_tracking_by_user_and_app(user, app)
            logging.info('got tracked_urls: %r' % tracked_urls)
            if tracked_urls.count(page_url) >= app.num_shows_before_tb:
                # user has viewed page more than once show top-bar-ask
                show_top_bar_ask = True

                # this number or more URLs tracked for (app and user)
                threshold = UNSURE_DETECTION['url_count_for_app_and_user']

                if len(tracked_urls) >= threshold:
                    # activate unsure_mutli_view (currently does nothing)
                    unsure_mutli_view = True

        # have client, app, user, and maybe instance
        try:
            app_css = app.get_css()  # only Shopify apps have CSS
        except AttributeError:
            app_css = ''  # it was not a SIBTShopify

        # Grab all template values
        template_values = {
            'debug': APP_LIVE_DEBUG,
            'URL': URL,

            'app': app,
            'sibt_version': app.version or 10,
            'app_css': app_css,
            'detect_shopconnection': True,

            'instance': instance,
            'is_live': is_live,
            'show_votes': show_votes,
            'show_top_bar_ask': str((show_top_bar_ask and (app.top_bar_enabled if app else True))),
            'unsure_multi_view': unsure_multi_view,
            'has_results': has_results,

            'user': user,
            'has_voted': has_voted,
            'is_asker': is_asker,
            'asker_name': asker_name,
            'asker_pic': asker_pic,

            'page_url': page_url,  # window.location
            'store_url': store_url,  # shopify url
            'store_domain': getattr (app.client, 'domain', ''),
            'store_id': self.request.get('store_id'),

            'product': product,

            'evnt': event,

            'FACEBOOK_APP_ID': app.settings['facebook']['app_id'],
            'fb_redirect'    : "%s%s" % (URL, url('ShowFBThanks')),
            'willt_code': link.willt_url_code if link else "",
        }

        # Finally, render the JS!
        path = os.path.join('apps/sibt/templates/', 'sibt.js')

        self.response.headers.add_header('P3P', P3P_HEADER)
        self.response.headers['Content-Type'] = 'text/javascript; charset=utf-8'
        self.response.out.write(template.render(path, template_values))
        return

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
            ScriptLoadAction.create(user, app, target)

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

