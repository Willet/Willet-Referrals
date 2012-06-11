#!/usr/bin/env python

__author__ = "Willet, Inc."
__copyright__ = "Copyright 2012, Willet, Inc"

import datetime
import logging
import os
import random
import urllib2

from urllib import urlencode
from urlparse import urlparse, urlunsplit

from django.utils import simplejson as json
from google.appengine.api import memcache
from google.appengine.ext.webapp import template

from apps.app.models import App
from apps.client.models import Client
from apps.link.models import Link
from apps.product.models import Product
from apps.sibt.actions import SIBTNoConnectFBCancelled, \
                              SIBTShowingButton, SIBTShowingAskIframe, \
                              SIBTShowingVote, SIBTShowingResults, \
                              SIBTShowingResultsToAsker, SIBTVoteAction
from apps.sibt.models import get_app, get_instance_event, get_products
from apps.sibt.models import SIBT, SIBTInstance, PartialSIBTInstance
from apps.sibt.shopify.models import SIBTShopify
from apps.user.models import User

from util.consts import ADMIN_IPS, DOMAIN, P3P_HEADER, PROTOCOL, SECURE_URL, \
                        SHOPIFY_APPS, UNSURE_DETECTION, URL, USING_DEV_SERVER
from util.helpers import get_target_url, url
from util.shopify_helpers import get_domain, get_shopify_url
from util.strip_html import strip_html
from util.urihandler import obtain, URIHandler


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

    @obtain('app_uuid', 'instance_uuid', 'user_uuid')
    def get(self, app_uuid, instance_uuid, user_uuid):
        """Shows the SIBT Ask page. Also used by SIBTShopify.

        params:
            url (required): the product URL; typically window.location.href
            products (required): UUIDs of all products to be included
                                 (first UUID will be primary product)

            store_url (optional): helps pinpoint the store
            user_uuid (optional)
            embed (optional): reduces size of window and removes some elements.
            instance_uuid (optional): if supplied, ask.html will not create
                                      a new instance. asks will be sent with
                                      this instance.
        """
        incentive_enabled = False
        instance = SIBTInstance.get(instance_uuid)  # None
        link = None
        origin_domain = os.environ.get('HTTP_REFERER', 'UNKNOWN')
        page_url = self.request.get('url', '') or \
                   self.request.get('page_url', '') or \
                   self.request.get('target_url', '') or \
                   self.request.get('refer_url', '') or \
                   self.request.headers.get('referer', '')  # NOT page url!
        product = None
        product_images = []
        store_url = ''
        template_products = []
        vendor = self.request.get('vendor', '')  # changes template used

        # We should absolutely have a user here, but they could have blocked their cookies
        user = User.get(user_uuid)
        user_found = hasattr(user, 'fb_access_token')

        # Store registration url (with backup options if it's missing)
        store_url = self.request.get('store_url', '') or page_url

        if not store_url:
            msg = "store_url not found in ask.html query string!"
            logging.error(msg)
            self.response.out.write(msg)
            return

        # have page_url, store_url
        app = get_app(urihandler=self)

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
        shopify_id = getattr(product, 'shopify_id', '')

        # see which template we should we using.
        try:
            if app.client and app.client.is_vendor:
                vendor = app.client.name
        except (NameError, AttributeError):
            pass  # not a vendor

        # successive steps to obtain the product(s) using any way possible
        products = get_products(urihandler=self)
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
                    'id': shopify_id,
                    'uuid': product.uuid,
                    'image': image,
                    'title': product.title,
                    'shopify_id': shopify_id,
                    'product_uuid': product.uuid,
                    'product_desc': strip_html(product.description),
                })
            else:
                logging.warning("Product not found in DB")

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
        if instance:
            link = instance.link  # re-use old link to get to this instance!
            logging.info("Reusing the link of an existing instance.")
        else:
            link = Link.create(page_url, app, origin_domain, user)

        # log this "showage"
        if user_found:
            SIBTShowingAskIframe.create(user, url=page_url, app=app)

        template_values = {
            'URL': URL,
            'title': "Which One ... Should I Buy This?",
            'debug': USING_DEV_SERVER or (self.request.remote_addr in ADMIN_IPS),
            'evnt': 'SIBTShowingAsk',
            'embed': bool(self.request.get('embed', '0') == '1'),

            'app': app,
            'app_uuid': app_uuid,
            'incentive_enabled': incentive_enabled,

            'user_email': user.get_attr('email') if user_found else None,
            'user_has_fb_token': 1 if user_found else 0,
            'user_name': user.get_full_name() if user_found else None,
            'user_pic': user.get_attr('pic') if user_found else None,
            'user_uuid': self.request.get('user_uuid'),

            'AB_share_text': "Should I buy this? Please let me know!",
            'instance_uuid': instance_uuid,
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

    VoteDynamicLoader handles two modes of operation:
    - new instance
    - existing instance

    params required for new instance:
        app_uuid: pinpoints the store
        products: uuids ('uuid,uuid,uuid') for the products to be shown.
                  SIBT and WOSIB modes are automatically managed.

    params required for existing instance:
        instance_uuid: show the vote page for this instance.
    """
    def get(self):
        app = None
        event = 'SIBTMakingVote'
        instance_uuid = self.request.get('instance_uuid')
        link = None
        new_instance = False  # True if this function creates one
        products = [] # populate this to show products on design page.
        share_url = ''
        sharing_message = ''
        store_url = get_shopify_url(self.request.get('store_url')) or \
                    get_shopify_url(self.request.get('page_url'))
        target = get_target_url(self.request.get('url', '')) or \
                 get_target_url(self.request.get('target_url', '')) or \
                 get_target_url(self.request.get('page_url', ''))
        template_values = {}
        user = User.get(self.request.get('user_uuid')) or \
               User.get_or_create_by_cookie(self, app=None)
        vendor = self.request.get('vendor', '')  # changes template used

        (instance, _) = get_instance_event(urihandler=self)
        if instance:
            logging.debug('instance found')

            if not instance.is_live:
                # We can't find the instance, so let's assume the vote is over
                self.response.out.write("This vote is now over.")
                return

            app = instance.app_
            if not app:  # We can't find the app?!
                self.response.out.write("This vote was not created properly.")
                return

            # record that the vote page was once opened.
            SIBTShowingVote.create(user=user, instance=instance)
            event = 'SIBTShowingVote'

            # In the case of a Shopify product, it will fetch from a .json URL.
            product = Product.get_or_fetch(instance.url, app.client)
            products = [Product.get(uuid) for uuid in instance.products]
        else:  # v11 mode: auto-create
            logging.debug('instance not found - creating one')

            app_uuid = self.request.get('app_uuid')
            if not app_uuid:
                self.response.out.write("This vote is now over.")

            app = get_app(urihandler=self)
            if not app:
                logging.error("Could not find SIBT app for %s" % store_url)
                self.response.out.write("Please register at http://rf.rs/s/shopify/beta "
                                        "to use this product.")
                return

            products = get_products(urihandler=self)
            if products:
                product_uuids = [product.uuid for product in products]
                logging.debug('app = %r' % app)
                logging.debug('target = %r' % target)
                logging.debug('product_uuids = %r' % product_uuids)
                instance = self.create_instance(app=app,
                                                page_url=target,
                                                product_uuids=product_uuids,
                                                sharing_message="")
                # update variables to reflect "creation"
                new_instance = True
                instance_uuid =  instance.uuid

        sharing_message = instance.sharing_message

        if instance.asker:
            name = instance.asker.get_full_name()

        if not link:
            link = instance.link
        try:
            share_url = link.get_willt_url()
        except AttributeError, e:
            logging.warn('Faulty link')

        # see which template we should we using.
        try:
            if app.client and app.client.is_vendor:
                vendor = app.client.name
        except NameError, AttributeError:
            pass  # not a vendor

        # sync the variables
        if not product:
            product = products[0]
        elif not products:
            products = [product]

        try:
            product_img = product.images[0]
        except:
            product_img = ''

        template_values = {
            'evnt': event,
            'product': product,
            'product_img': product_img,
            'app': app,
            'URL': URL,
            'instance_uuid': instance_uuid,

            'user': user,
            'asker_name': name if name else "your friend",
            'asker_pic': instance.asker.get_attr('pic'),
            'is_asker': user.key() == instance.asker.key(),
            'target_url': target,
            'fb_comments_url': '%s' % (link.get_willt_url()),
            'new_instance': new_instance,
            # 'percentage': percentage,
            'products': products,
            'share_url': share_url,
            'sharing_message': strip_html(sharing_message),
            'product_url': product.resource_url,
            'store_url': app.store_url,
            'store_name': app.store_name,
            'instance': instance,
            # 'votes': yesses + nos,
            # 'yesses': instance.get_yesses_count(),
            # 'noes': instance.get_nos_count(),
            'ask_qs': urlencode({'app_uuid': app.uuid,
                                 'instance_uuid': instance.uuid,  # golden line
                                 'user_uuid': instance.asker.uuid,
                                 'products': ','.join(instance.products),
                                 'product_uuid': product.uuid,
                                 'page_url': target,
                                 'store_url': app.store_url,
                                 'embed': 1})
        }

        filename = 'vote-multi.html' if len(products) > 1 else 'vote.html'
        path = os.path.join('apps/sibt/templates', vendor, filename)
        if not os.path.exists(path):
            path = os.path.join('apps/sibt/templates', filename)

        self.response.headers.add_header('P3P', P3P_HEADER)
        self.response.out.write(template.render(path, template_values))
        return

    def create_instance(self, app, page_url, product_uuids=None,
                        sharing_message=""):
        """Helper to create an instance without question."""
        user = User.get_or_create_by_cookie(self, app)

        logging.debug('domain = %r' % get_domain(page_url))
        # the href will change as soon as the instance is done being created!
        link = Link.create(targetURL=page_url,
                           app=app,
                           domain=get_shopify_url(page_url),
                           user=user)

        product = Product.get_or_fetch(page_url, app.client)  # None
        if not product_uuids:
            try:
                product_uuids = [product.uuid]  # [None]
            except AttributeError:
                product_uuids = []
        instance = app.create_instance(user=user,
                                       end=None,
                                       link=link,
                                       dialog="",
                                       img="",
                                       motivation=None,
                                       sharing_message="",
                                       products=product_uuids)

        # after creating the instance, switch the link's URL right back to the
        # instance's vote page
        link.target_url = urlunsplit([PROTOCOL,
                                      DOMAIN,
                                      url('VoteDynamicLoader'),
                                      ('instance_uuid=%s' % instance.uuid),
                                      ''])
        logging.info("link.target_url changed to %s" % link.target_url)
        link.put()

        return instance


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
                'evnt': event,
                'product_img': product.images,
                'app': app,
                'URL': URL,
                'user': user,
                'asker_name': name if name != '' else "your friend",
                'asker_pic': instance.asker.get_attr('pic'),
                'target_url': target,
                'fb_comments_url': '%s#code=%s' % (target, link.willt_url_code),

                'share_url': share_url,
                'is_asker': is_asker,
                'is_live': has_voted,  # same thing?
                'instance': instance,
                'instance_ends': '%s%s' % (instance.end_datetime.isoformat(), 'Z'),

                'vote_percentage': vote_percentage,
                'total_votes': total
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
        product = None

        if not partial:
            logging.warn('PartialSIBTInstance is already gone')
            return  # there's nothing we can do now

        if post_id != "":
            user_cancelled = False

            # Grab stuff from PartialSIBTInstance
            try:
                app = partial.app_
                link = partial.link
                product = getattr(partial, 'product', None)
                products = getattr(partial, 'products', [])
            except AttributeError, err:
                logging.error("partial is: %s (%s)" % (partial, err))

            try:
                if not product and products and products[0]:
                    logging.info('instance with no product but with '
                                 'products - using products[0] as product')
                    product = Product.get(products[0])
                product_image = product.images[0]
            except:
                logging.warn('product has no image - resorting to blank')
                product_image = '%s/static/imgs/blank.png' % URL # blank

            # Make the Instance!
            instance = app.create_instance(user=user,
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
            'DOMAIN': DOMAIN,
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


class SIBTInstanceStatusChecker(URIHandler):
    """Lightweight view for visitors to check their instances' statuses.

    Checks visitors (with their cookies) whether they have made an instance,
    and, if true, return if the instance is still valid (not expired).

    This handler is GET-only. All other methods raise NotImplementedError.
    """
    @obtain('instance_uuids')
    def get(self, instance_uuids):
        """Result is a serialised json object.

        {
            "uuid": "(uuid of the most recently active instance)"
                    OR
                    "(empty string if no active instances)",
            "products": ["(product_uuid)", "(product_uuid)", ...]
                        OR
                        [(empty array if no active instances)]
                        OR
                        [(empty array if SIBT single product mode)],

            ... future expansion possible
        }
        """
        instances = []  # objects
        iul = []  # short for Instance-Uuid-List
        mr_instance = None  # most recent instance
        output = {'uuid': '',
                  'products': []}  # will be serialised

        if instance_uuids:  # "perform checks on an instance"
            iul = unicode(instance_uuids).split(',')  # [u'1', u'2', u'3']

        if len(iul):  # if list of uuids is non-empty
            instances = [SIBTInstance.get(uuid) for uuid in iul]
            for instance in instances:
                if not instance:
                    continue  # instance is None, skip it
                if not instance.is_live:
                    continue  # instance is expired, skip it

                if not mr_instance:
                    # if most recent instance is still empty, register one
                    mr_instance = instance
                elif instance.created > mr_instance.created:
                    mr_instance = instance  # this instance is more recent

        if mr_instance:  # found one most recent, active instance
            output['uuid'] = mr_instance.uuid
            output['products'] = mr_instance.products

        self.response.headers.add_header('P3P', P3P_HEADER)
        self.response.out.write(json.dumps(output))
        return


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
        app = None
        app_css = ''
        asker_name = ''
        asker_pic = ''
        client = None
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
        show_top_bar_ask = False
        store_url = get_shopify_url(self.request.get('store_url'))
        template_values = {}
        tracked_urls = []
        unsure_multi_view = False
        user = None
        vendor_name = ''
        votes_count = 0
        willet_code = self.request.get('willt_code', '')

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
        if app:
            # read client from DB only if needed
            client = app.client

        if not client:
            client = Client.get_by_url(store_url)
            if not app and client:
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

        # see if we should run this script as a vendor.
        vendor_name = getattr(client, 'name', '') if client.is_vendor else ''

        # have page_url, store_url, app, client. fetch everything!
        user = User.get_or_create_by_cookie(self, app)
        product = Product.get_or_fetch(page_url, client)
        (instance, event) = get_instance_event(urihandler=self,
                                               app=app,
                                               user=user,
                                               page_url=page_url,
                                               willet_code=willet_code)

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
                    app.put_later()
            except:
                pass  # can't decode target as URL; oh well!

        try:
            product_title = json.dumps(product.title)
            product_description = json.dumps(product.description)
        except:
            product_title = 'false'
            product_description = 'false'
        # let it pass - sibt.js will attempt to create product

        # If we have an instance, figure out if
        # a) Is User asker?
        # b) Has this User voted?
        if instance and instance.asker and user:
            is_asker = bool(instance.asker.key() == user.key())
            is_live = instance.is_live
            event = 'SIBTShowingResults'

        # an instance is pretended not to exist if it is not live.
        if instance and is_live:
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
            if not app_css:
                raise AttributeError('Empty CSS is illegal!')
        except AttributeError:
            app_css = SIBTShopify.get_default_css()

        # indent like this: http://stackoverflow.com/questions/6388187
        template_values = {
            # general things
            'debug': USING_DEV_SERVER or (self.request.remote_addr in ADMIN_IPS),
            'DOMAIN': DOMAIN,
            'URL': URL,

            # store info
            'client': client,
            'page_url': page_url,  # current page
            'store_url': store_url,  # registration url
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
            'has_voted': has_voted,
            'is_asker': is_asker,
            'unsure_multi_view': unsure_multi_view,

            # misc.
            'FACEBOOK_APP_ID': SHOPIFY_APPS['SIBTShopify']['facebook']['app_id'],
            'fb_redirect': "%s%s" % (URL, url('ShowFBThanks')),
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
        self.redirect("%s%s?%s" % (SECURE_URL,
                                   url('SIBTServeScript'),
                                   self.request.query_string),
                      permanent=True)
        return