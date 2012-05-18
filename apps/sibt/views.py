#!/usr/bin/env python

__author__ = "Willet, Inc."
__copyright__ = "Copyright 2012, Willet, Inc"

import datetime
import logging
import os
import random
import re

from urlparse import urlparse, urlunsplit

from django.utils import simplejson as json
from google.appengine.api import memcache
from google.appengine.ext.webapp import template

from apps.app.models import App
from apps.client.models import Client
from apps.gae_bingo.gae_bingo import ab_test, bingo
from apps.link.models import Link
from apps.product.models import Product
from apps.product.shopify.models import ProductShopify
from apps.sibt.actions import *
from apps.sibt.models import SIBT, SIBTInstance, PartialSIBTInstance
from apps.user.models import User

from util.consts import *
from util.helpers import *
from util.shopify_helpers import get_shopify_url
from util.strip_html import strip_html
from util.urihandler import URIHandler


class ShowBetaPage(URIHandler):
    """Shows the introduction page, containing AJAX functions to create app."""
    def get(self):
        path = os.path.join('apps/sibt/templates/', 'beta.html')
        self.response.out.write(template.render(path, {
            'URL': URL,
            'sibt_version': SIBT.CURRENT_INSTALL_VERSION
        }))


class AskDynamicLoader(URIHandler):
    """Serves a plugin that will contain various functionality

    for sharing information about a purchase just made by one of our clients
    """

    def get(self):
        """Shows the SIBT Ask page. Also used by SIBTShopify.

        params:
            url (required): the product URL; typically window.location.href
            products (required): UUIDs of all products to be included
                                 (first UUID will be primary product)

            user_uuid (optional)
        """
        app_uuid = self.request.get('app_uuid')
        instance_uuid = self.request.get('instance_uuid')
        fb_app_id = SHOPIFY_APPS['SIBTShopify']['facebook']['app_id']
        incentive_enabled = False
        origin_domain = os.environ.get('HTTP_REFERER', 'UNKNOWN')
        page_url = self.request.get('url', '') or \
                   self.request.get('page_url', '') or \
                   self.request.get('target_url', '') or \
                   self.request.get('refer_url', '') or \
                   self.request.headers.get('referer', '')  # NOT page url!
        product = product_shopify = None
        product_images = []
        product_desc = []
        store_url = ''
        template_products = []
        vendor = self.request.get('vendor', '')  # changes template used

        # We should absolutely have a user here, but they could have blocked their cookies
        user = User.get(self.request.get('user_uuid'))
        user_found = hasattr(user, 'fb_access_token')
        user_is_admin = user.is_admin() if isinstance(user , User) else False

        def get_products(app=None):
            """Fetch products.

            Order of precedence:
            - product UUIDs
            - product Shopify IDs
            - product UUID
            - product Shopify ID
            - page url
            """
            # at least one of these must be present to initiate an ask.
            products = []
            product_shopify_id = self.request.get('product_shopify_id', '')
            product_uuid = self.request.get('product_uuid', '')
            product_uuids = self.request.get('products', '').split(',')
            product_ids = self.request.get('ids', '').split(',')

            products = [Product.get(uuid) for uuid in product_uuids]
            if products[0]:
                logging.debug("get products by UUIDs, got %r" % products)
                return products

            products = [ProductShopify.get_by_shopify_id(id) \
                        for id in product_ids]
            if products[0]:
                logging.debug("get products by Shopify IDs, got %r" % products)
                return products

            products = [Product.get(product_uuid)]
            if products[0]:
                logging.debug("get products by UUID, got %r" % products)
                return products

            products = [ProductShopify.get_by_shopify_id(product_uuid)]
            if products[0]:
                logging.debug("get products by Shopify ID, got %r" % products)
                return products

            if page_url and app:
                products = [Product.get_or_fetch(page_url, app.client)]
            return products

        # Store registration url (with backup options if it's missing)
        store_url = self.request.get('store_url', '') or page_url

        if not store_url:
            msg = "store_url not found in ask.html query string!"
            logging.error(msg)
            self.response.out.write(msg)
            return

        # have page_url, store_url
        app = SIBT.get_by_store_url(store_url)
        if not app and store_url:
            url_parts = urlparse(store_url)
            # all db entries are currently http; makes sure https browsers
            # can also get app.
            store_url = "http://%s" % url_parts.netloc
            app = SIBT.get_by_store_url(store_url)  # re-get

        if not app:
            logging.error("Could not find SIBT app for %s" % store_url)
            self.response.out.write("Please register at http://rf.rs/s/shopify/beta to use this product.")
            return
        elif not hasattr(app, 'client'):
            logging.error("SIBT app has no client. Probably uninstall.")
            self.response.out.write("Please register at http://rf.rs/s/shopify/beta to use this product.")
            return
        logging.debug("app = %r" % app)

        # if both are present and extra_url needs to be filled...
        if store_url and page_url and not hasattr(app, 'extra_url'):
            """Checks if page_url (almost always window.location.href)
            has the same domain as store url
            If true, save the alternative URL so it can be called back later.

            Example: http://social-referral.appspot.com/s/ask.html?
                     store_url=http://thegoodhousewife.myshopify.com
                    &page_url=http://thegoodhousewife.co.nz/cart&...
            """
            try:
                url_parts = urlparse(page_url)
                if url_parts.scheme and url_parts.netloc:
                    # is "abc.myshopify.com" part of the store URL, "http://abc.myshopify.com"?
                    if url_parts.netloc not in urllib2.unquote(store_url):
                        logging.info("[SIBT] associating a new URL, %s, "
                                    "with the original, %s" % (app.extra_url,
                                                                app.store_url))
                        app.extra_url = "%s://%s" % (url_parts.scheme,
                                                    url_parts.netloc)
                        app.put()
            except:
                logging.error("Could not save app extra_url", exc_info=True)
                pass  # failure is, in fact, an option.

        incentive_enabled = getattr(app, 'incentive_enabled', False)
        product_shopify_id = getattr(product, 'shopify_id', '')

        # see which template we should we using.
        try:
            if app.client and app.client.vendor:
                vendor = app.client.name
        except NameError, AttributeError:
            pass  # not a vendor

        # successive steps to obtain the product(s) using any way possible
        products = get_products(app=app)
        if not products[0]:  # we failed to find a single product!
            logging.error("Could not find products; quitting")
            self.response.out.write("Products requested are not in our database yet.")
            return

        # have store_url, app, products; build template products
        for product in products:
            if product:  # could be None of Product is somehow not in DB
                if len(product.images) > 0:
                    image = product.images[0] # can't catch LIOOR w/try
                else:
                    image = '/static/imgs/noimage-willet.png'

                template_products.append({
                    'id': product_shopify_id,
                    'uuid': product.uuid,
                    'image': image,
                    'title': product.title,
                    'shopify_id': product_shopify_id,
                    'product_uuid': product.uuid,
                    'product_desc': product.description,
                })
            else:
                logging.warning("Product of UUID %s not found in DB" % uuid)

        if not template_products:
            """do not raise ValueError - "UnboundLocalError:
            local variable 'ValueError' referenced before assignment"
            """
            raise Exception('UUIDs did not correspond to products')

        # compile list of product images (one image from each product)
        product_images = [prod['image'] for prod in template_products]
        logging.debug("product images: %r" % product_images)

        # have store_url, app, products, template_products, product_images
        random_product = random.choice(template_products)
        random_image = random_product['image']
        if not page_url: # if somehow it's still missing, fix the missing url
            page_url = products[0].resource_url

        # Make a new Link.
        # we will be replacing this target url with the vote page url once
        # we get an instance.
        link = Link.create(page_url, app, origin_domain, user)

        # log this "showage"
        if user_found:
            SIBTShowingAskIframe.create(user, url=page_url, app=app)

        # Which share message should we use?
        ab_share_options = [
            "I'm not sure if I should buy this. What do you think?",
            "Would you buy this? I need help making a decision!",
            "I need some shopping advice. Should I buy this? Would you?",
            "Desperately in need of some shopping advice! Should I buy this? Would you? Vote here.",
        ]

        if user_is_admin:
            ab_opt = "ADMIN: Should I buy this? Please let me know!"
        else:
            ab_opt = ab_test('sibt_share_text3',
                             ab_share_options,
                             user=user,
                             app=app)

        template_values = {
            'URL' : URL,
            'title' : "Which One ... Should I Buy This?",

            'app': app,
            'app_uuid': app_uuid,
            'incentive_enabled': incentive_enabled,

            'user_email': user.get_attr('email') if user_found else None,
            'user_has_fb_token': 1 if user_found else 0,
            'user_name': user.get_full_name() if user_found else None,
            'user_pic': user.get_attr('pic') if user_found else None,
            'user_uuid': self.request.get('user_uuid'),

            'AB_share_text': ab_opt,
            'instance_uuid': self.request.get('instance_uuid'),
            'evnt': self.request.get('evnt'),
            'FACEBOOK_APP_ID': SHOPIFY_APPS['SIBTShopify']['facebook']['app_id'],
            'fb_redirect': "%s%s" % (URL, url('ShowFBThanks')),
            'willt_code': link.willt_url_code, # used to create full instances
            'share_url': link.get_willt_url(), # page_url
            'store_domain': store_url,
            'target_url': page_url,

            'image': random_image,
           # random_product will be THE product on single-product mode.
            'product_desc': random_product['product_desc'],
            'product_images': product_images,
            'product_title': products[0].title or "",
            'product_uuid': products[0].uuid,  # deprecated
            #'products': quoted_join(product_uuids),
            'products': template_products,
        }

        # render SIBT/WOSIB
        filename = 'ask-multi.html' if len(template_products) > 1 else 'ask.html'
        path = os.path.join('apps/sibt/templates', vendor, filename)
        if not os.path.exists(path):
            path = os.path.join('apps/sibt/templates', filename)

        self.response.headers.add_header('P3P', P3P_HEADER)
        self.response.out.write(template.render(path, template_values))
        return


class VoteDynamicLoader(URIHandler):
    """ Serves a plugin where people can vote on one or more products.

    On v10 and up (standalone vote page), "voter is never asker"
    """
    def get(self):
        app = None
        instance_uuid = self.request.get('instance_uuid')
        link = None
        products = [] # populate this to show products on design page.
        share_url = ''
        target = get_target_url(self.request.get('url', ''))
        template_values = {}
        user = None
        vendor = self.request.get('vendor', '')  # changes template used
        willt_code = self.request.get('willt_code')

        def get_instance():
            """successive stages to get instance."""
            link = None

            # stage 1: get instance by instance_uuid
            instance = SIBTInstance.get(instance_uuid)
            if instance:
                return instance

            # stage 2: get instance by willet code in URL
            # using willet code (fast) or raw DB lookup (slower)
            if willt_code:
                logging.info('trying to get instance for code: %s' % willt_code)
                link = Link.get_by_code(willt_code)
                if not link:
                    link = Link.all()\
                               .filter('user =', user)\
                               .filter('target_url =', target)\
                               .filter('app_ =', app)\
                               .get()
            if link:
                instance = link.sibt_instance.get()
            if instance:
                return instance

            # stage 3: get instance by user and URL
            if user and target:
                instance = SIBTInstance.get_by_asker_for_url(user, target)
            return instance  # could be none

        instance = get_instance()
        if not instance:
            # We can't find the instance, so let's assume the vote is over
            self.response.out.write("This vote is now over.")
            return

        app = instance.app_
        if not app:
            # We can't find the app?!
            self.response.out.write("Drat! This vote was not created properly.")
            return

        # see which template we should we using.
        try:
            if app.client and app.client.vendor:
                vendor = app.client.name
        except NameError, AttributeError:
            pass  # not a vendor


        user = User.get(self.request.get('user_uuid')) or \
               User.get_or_create_by_cookie(self, app)

        name = instance.asker.get_full_name()

        if not link:
            link = instance.link
        try:
            share_url = link.get_willt_url()
        except AttributeError, e:
            logging.warn ('Faulty link')

        # record that the vote page was once opened.
        SIBTShowingVote.create(user=user, instance=instance)
        event = 'SIBTShowingVote'

        # In the case of a Shopify product, it will fetch from a .json URL.
        product = Product.get_or_fetch(instance.url, app.client)
        products = [Product.get(uuid) for uuid in instance.products]

        if not product:
            product = products[0]
        elif not products:
            products = [product]

        try:
            product_img = product.images[0]
        except:
            product_img = ''

        yesses = instance.get_yesses_count()
        nos = instance.get_nos_count()
        try:
            percentage = yesses / float(yesses + nos)
        except ZeroDivisionError:
            percentage = 0.0 # "it's true that 0% said buy it"

        template_values = {
            'evnt' : event,
            'product': product,
            'product_img': product_img,
            'app' : app,
            'URL': URL,
            'instance_uuid' : instance_uuid,

            'user': user,
            'asker_name' : name if name else "your friend",
            'asker_pic' : instance.asker.get_attr('pic'),
            'target_url' : target,
            'fb_comments_url' : '%s' % (link.get_willt_url()),
            'percentage': percentage,
            'products': products,
            'share_url': share_url,
            'product_url': product.resource_url,
            'store_url': app.store_url,
            'store_name': app.store_name,
            'instance' : instance,
            'votes': yesses + nos,
            'yesses': instance.get_yesses_count(),
            'noes': instance.get_nos_count()
        }

        filename = 'vote-multi.html' if len(products) > 1 else 'vote.html'
        path = os.path.join('apps/sibt/templates', vendor, filename)
        if not os.path.exists(path):
            path = os.path.join('apps/sibt/templates', filename)

        self.response.headers.add_header('P3P', P3P_HEADER)
        self.response.out.write(template.render(path, template_values))
        return


class ShowResults(URIHandler):
    """Shows the results of a 'Should I Buy This?'"""
    def get(self):
        app = None
        event = 'SIBTShowingResultsToFriend'  # default event
        has_voted = False
        instance_uuid = self.request.get('instance_uuid')
        link = None
        target = get_target_url(self.request.get('url'))
        template_values = {}
        user = User.get(self.request.get('user_uuid'))
        willet_code = self.request.get('willt_code')

        # successive stages to get instance
        # stage 1: get instance by instance_uuid
        instance = SIBTInstance.get_by_uuid(self.request.get('instance_uuid'))

        # stage 2: get instance by willet code in URL
        if not instance and willet_code:
            logging.info('trying to get instance for code: %s' % willet_code)
            link = Link.get_by_code(self.request.get('willt_code'))
            if not link:
                # no willt code, asker probably came back to page with
                # no hash code
                link = Link.all()\
                            .filter('user =', user)\
                            .filter('target_url =', target)\
                            .filter('app_ =', app)\
                            .get()
                logging.info('got link by page_url %s: %s' % (target, link))
            if link:
                instance = link.sibt_instance.get()

        # stage 3: get instance by user and URL
        if not instance and user and target:
            instance = SIBTInstance.get_by_asker_for_url(user, target)

        # still no instance? fail
        if not instance:
            self.response.out.write("The vote is over.")
            return

        # have instance
        # start looking for instance info
        if not app:
            app = instance.app_

        if not user and app:
            user = User.get_or_create_by_cookie(self, app)

        name = instance.asker.get_full_name()

        winning_products = instance.get_winning_products()
        if len(winning_products) > 1:  # WOSIB - many products tie
            # that is, if multiple items have the same score
            template_values = {
                'products': winning_products,
            }
            # Finally, render the HTML!
            path = os.path.join('apps/sibt/templates/', 'results-multi.html')
        elif len(instance.products) > 1 and len(winning_products) == 1:
            # WOSIB - one product wins
            try:
                product_image = winning_products[0].images[0]
            except:
                product_image = '/static/imgs/noimage-willet.png' # no image default

            try:
                product_link = winning_products[0].resource_url
            except:
                product_link = '' # no link default

            template_values = {
                'product': winning_products[0],
                'product_image': product_image,
                'has_product_link': bool(product_link),
                'product_link': product_link
            }
            # Finally, render the HTML!
            path = os.path.join('apps/sibt/templates/', 'results-uni.html')
        else:
            # SIBT - product YES/NO
            yesses = instance.get_yesses_count()
            noes = instance.get_nos_count()
            name = instance.asker.get_full_name()
            is_asker = (instance.asker.key() == user.key())

            if not is_asker:
                vote_action = SIBTVoteAction.get_by_app_and_instance_and_user(app, instance, user)

                logging.info('got vote action: %s' % vote_action)
                has_voted = bool(vote_action != None)

            if not instance.is_live:
                has_voted = True

            if is_asker:
                SIBTShowingResultsToAsker.create(user=user, instance=instance)
                event = 'SIBTShowingResultsToAsker'
            elif has_voted:
                SIBTShowingResults.create(user=user, instance=instance)
            else:
                SIBTShowingVote.create(user=user, instance=instance)

            if link == None:
                link = instance.link
            share_url = link.get_willt_url()

            # calculate vote percentage
            total = yesses + noes
            if total == 0:
                vote_percentage = None
            else:
                vote_percentage = str(int(float(float(yesses)/float(total))*100))

            product = Product.get_or_fetch(instance.url, app.client)

            template_values = {
                'evnt' : event,
                'product_img': product.images,
                'app' : app,
                'URL': URL,
                'user': user,
                'asker_name' : name if name != '' else "your friend",
                'asker_pic' : instance.asker.get_attr('pic'),
                'target_url' : target,
                'fb_comments_url' : '%s#code=%s' % (target, link.willt_url_code),

                'share_url': share_url,
                'is_asker' : is_asker,
                'is_live': has_voted,  # same thing?
                'instance' : instance,
                'instance_ends': '%s%s' % (instance.end_datetime.isoformat(), 'Z'),

                'vote_percentage': vote_percentage,
                'total_votes' : total
            }
            path = os.path.join('apps/sibt/templates/', 'results.html')

        # Finally, render the HTML!
        self.response.headers.add_header('P3P', P3P_HEADER)
        self.response.out.write(template.render(path, template_values))
        return


class ShowFBThanks(URIHandler):
    """Called to show fb_thanks.html.

    We know the user just shared on FB, so create an instance etc.
    """

    # http://barbara-willet.appspot.com/s/fb_thanks.html?post_id=122604129_220169211387499#_=_
    def get(self):
        incentive_enabled = False
        user_cancelled = True
        app = None
        post_id = self.request.get('post_id') # from FB
        user = User.get_by_cookie(self)
        partial = PartialSIBTInstance.get_by_user(user)

        if post_id != "":
            user_cancelled = False

            # GAY BINGO
            if not user.is_admin():
                bingo('sibt_fb_no_connect_dialog')

            # Grab stuff from PartialSIBTInstance
            try:
                app = partial.app_
                link = partial.link
                product = partial.product
                products = partial.products
            except AttributeError, err:
                logging.error("partial is: %s (%s)" % (partial, err))

            try:
                product_image = product.images[0]
            except:
                product_image = '%s/static/imgs/blank.png' % URL # blank

            # Make the Instance!
            instance = app.create_instance(user,
                                           end=None,
                                           link=link,
                                           img=product_image,
                                           motivation=None,
                                           dialog="NoConnectFB",
                                           sharing_message="",
                                           products=products)

            # partial's link is actually bogus (points to vote.html without an instance_uuid)
            # this adds the full SIBT instance_uuid to the URL, so that the vote page can
            # be served.
            link.target_url = urlunsplit([PROTOCOL,
                                          DOMAIN,
                                          url('VoteDynamicLoader'),
                                          ('instance_uuid=%s' % instance.uuid),
                                          ''])
            logging.info ("link.target_url changed to %s (%s)" % (
                           link.target_url, instance.uuid))

            # increment link stuff
            link.app_.increment_shares()
            link.add_user(user)
            link.put()
            link.memcache_by_code() # doubly memcached
            logging.info('incremented link and added user')
        elif partial != None:
            # Create cancelled action
            SIBTNoConnectFBCancelled.create(user,
                                            url=partial.link.target_url,
                                            app=partial.app_)

        if partial:
            # Now, remove the PartialSIBTInstance. We're done with it!
            partial.delete()

        template_values = {
            'email': user.get_attr('email'),
            'user_cancelled': user_cancelled,
            'incentive_enabled': app.incentive_enabled if app else False
        }

        path = os.path.join('apps/sibt/templates/', 'fb_thanks.html')
        self.response.headers.add_header('P3P', P3P_HEADER)
        self.response.out.write(template.render(path, template_values))
        return


class ColorboxJSServer(URIHandler):
    """ Called to load Colorbox.js """
    def get(self):
        template_values = {
            'URL': URL,
            'app_uuid': self.request.get('app_uuid'),
            'user_uuid': self.request.get('user_uuid'),
            'instance_uuid': self.request.get('instance_uuid'),
            'target_url': self.request.get('target_url')
        }

        path = os.path.join('apps/sibt/templates/js/', 'jquery.colorbox.js')
        self.response.headers["Content-Type"] = "text/javascript"
        self.response.headers.add_header('P3P', P3P_HEADER)
        self.response.out.write(template.render(path, template_values))
        return


class ShowOnUnloadHook(URIHandler):
    """ Creates a local-domain iframe that allows SJAX requests to be served
        when the window unloads. (Typically, webkit browsers do not complete
        onunload functions unless a synchronous AJAX is sent onbeforeunload,
        and in order to send synced requests, the request must be sent to the
        same domain.)
    """
    def get(self):
        template_values = {
            'URL': URL,
            'app_uuid': self.request.get('app_uuid'),
            'user_uuid': self.request.get('user_uuid'),
            'instance_uuid': self.request.get('instance_uuid'),
            'target_url': self.request.get('target_url'),
            'evnt': self.request.get('evnt')
        }

        path = os.path.join('apps/sibt/templates/', 'onunloadhook.html')
        self.response.headers.add_header('P3P', P3P_HEADER)
        self.response.out.write(template.render(path, template_values))
        return


class SIBTGetUseCount (URIHandler):
    """Outputs the number of times the SIBT app has been used.

    This handler is GET-only. All other methods raise NotImplementedError.
    """
    def get(self):
        """Returns number of button loads divided by 100."""
        try:
            product_uuid = self.request.get ('product_uuid')
            button_use_count = memcache.get ("usecount-%s" % product_uuid)
            if button_use_count is None:
                button_use_count = int (SIBTShowingButton.all().count() / 100)
                memcache.add ("usecount-%s" % product_uuid, button_use_count)
            self.response.out.write (str (button_use_count))
        except:
            self.response.out.write ('0') # no shame in that?


class SIBTServeScript(URIHandler):
    """Serves a script that shows the SIBT button.

    This handler is now GET-only. All other methods raise NotImplementedError.
    """
    def get(self):
        """Serves a script that shows the SIBT button.

        Due to the try-before-you-buy nature of the Internets, this view will
        not create a SIBT app for the store/domain unless the site owner has
        already registered with us.

        Example call: http://brian-willet.appspot.com/s/sibt.js?url=http%3A%...
        2F%2Fkiehn-mertz3193.myshopify.com%2Fproducts%2Fcustomer-focused-lea...
        ding-edge-algorithm

        SIBT is activated on the page using any of these methods:
        {% include "willet_sibt" %} (the Shopify snippet)
        <div id="_willet_buttons_app"></div> (Buttons app, as SIBT Connection)
        <div class="_willet_sibt" (...)><script src='(above)'> (SIBT-JS)

        A None client is NORMAL.
        None Clients indicate an uninstalled App. Do not serve script.

        Required params: url/page_url (the page URL)
                         store_url (the store's registration url)
                         client_uuid (the client UUID)
        Optional params: willt_code (helps find instance)
        """
        # declare vars.
        admin_testing_on_live = False
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
        product_title = 'false'  # must be a javascript variable
        product_description = 'false'  # must be a javascript variable
        show_votes = False
        show_top_bar_ask = False
        store_url = get_shopify_url(self.request.get('store_url'))
        template_values = {}
        unsure_multi_view = False
        use_db_analytics = False
        use_google_analytics = True
        user = None
        vendor_name = ''
        votes_count = 0
        willet_code = self.request.get('willt_code')

        def get_instance_event():
            """Returns an (instance, event) tuple for this pageload,
            if there is an instance.
            """
            instance = SIBTInstance.get_by_asker_for_url(user, page_url)
            if instance:
                return (instance, 'SIBTShowingResults')

            if willet_code:
                link = Link.get_by_code(willet_code)
                if link:
                    instance = link.sibt_instance.get()
                if instance:
                    return (instance, 'SIBTShowingResults')

            if user:
                instances = SIBTInstance.all(keys_only=True)\
                                        .filter('url =', page_url)\
                                        .fetch(100)
                key_list = [key.id_or_name() for key in instances]
                action = SIBTClickAction.get_for_instance(app, user, page_url,
                                                          key_list)
                if action:
                    instance = action.sibt_instance

                if instance:
                    return (instance, 'SIBTShowingVote')

            return (None, '')


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
        if not store_url and page_url:
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
        app = SIBT.get_by_store_url(store_url)  # could come as SIBTShopify
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
            """Check if target (almost always window.location.href) has the
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
                pass  # can't decode target as URL; oh well!

        user = User.get_or_create_by_cookie(self, app)
        product = Product.get_or_fetch(page_url, client)
        try:
            product_title = json.dumps(product.title)
            product_description = json.dumps(product.description)
        except:
            product_title = 'false'
            product_description = 'false'
        # let it pass - sibt.js will attempt to create product

        instance, event = get_instance_event()

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
                time_diff = datetime.datetime.now() - instance.created
                logging.debug ("time_diff = %s" % time_diff)
                if time_diff <= datetime.timedelta(days=1):
                    has_results = True
            logging.debug ("has_results = %s" % has_results)

        # unsure detection
        # this must be created to track view counts.
        SIBTShowingButton.create(app=app, url=page_url, user=user)
        if app and not instance:
            tracked_urls = SIBTShowingButton.get_tracking_by_user_and_app(user, app)
            logging.info('got tracked_urls: %r' % tracked_urls)
            if tracked_urls.count(page_url) >= app.num_shows_before_tb:
                # user has viewed page more than once show top-bar-ask
                show_top_bar_ask = True

            # this number or more URLs tracked for (app and user)
            threshold = UNSURE_DETECTION['url_count_for_app_and_user']
            logging.debug('len(tracked_urls) = %d' % len(tracked_urls))
            if len(tracked_urls) >= threshold:
                # activate unsure_multi_view (bottom popup)
                unsure_multi_view = True

        # have client, app, user, and maybe instance
        try:
            app_css = app.get_css()  # only Shopify apps have CSS
        except AttributeError:
            app_css = ''  # it was not a SIBTShopify

        # see if we should run this script as a vendor.
        vendor_name = getattr(client, 'name', '') if client.vendor else ''

        # indent like this: http://stackoverflow.com/questions/6388187
        template_values = {
            # general things
            'debug': APP_LIVE_DEBUG or (self.request.remote_addr in ADMIN_IPS),
            'URL': URL,

            # store info
            'client': client,
            'page_url': page_url,  # current page
            'store_url': store_url,  # registration url
          # 'store_id': getattr(app, 'store_id', ''),
            'vendor': vendor_name,  # triggers vendor modes

            # app info
            'app': app, # if missing, django omits these silently
            'app_css': app_css, # SIBT-JS does not allow custom CSS.
            'sibt_version': app.version or App.CURRENT_INSTALL_VERSION,

            # instance info
            'instance': instance,
            'evnt': event,
            'has_results': has_results,
            'is_live': is_live,
            'show_top_bar_ask': show_top_bar_ask and app.top_bar_enabled,
            'show_votes': False, # this is annoying if True

            # product info
            'has_product': bool(product),
            'product': product,
            'product_title': product_title,
            'product_description': product_description,

            # user info
            'user': user,
            'asker_name': asker_name,
            'asker_pic': asker_pic,
            'is_asker': is_asker,
            'unsure_multi_view': unsure_multi_view,

            # misc.
            'FACEBOOK_APP_ID': SHOPIFY_APPS['SIBTShopify']['facebook']['app_id'],
            'fb_redirect': "%s%s" % (URL, url('ShowFBThanks')),
            'use_db_analytics': use_db_analytics,
            'use_google_analytics': use_google_analytics,
            'willt_code': link.willt_url_code if link else "",
        }

        path = os.path.join('apps/sibt/templates/', 'sibt.js')
        self.response.headers.add_header('P3P', P3P_HEADER)
        self.response.headers['Content-Type'] = 'text/javascript; charset=utf-8'
        self.response.out.write(template.render(path, template_values))
        return


class SIBTShopifyServeScript(URIHandler):
    """Does everything SIBTServeScript does."""
    def get(self):
        """Does everything SIBTServeScript does."""
        self.redirect("%s%s?%s" % (URL,
                                   url('SIBTServeScript'),
                                   self.request.query_string),
                      permanent=True)
        return