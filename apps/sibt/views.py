#!/usr/bin/env python

__author__ = "Willet, Inc."
__copyright__ = "Copyright 2012, Willet, Inc"

import logging
import os
import re

from urlparse import urlparse, urlunsplit

from google.appengine.api import memcache
from google.appengine.api import taskqueue
from google.appengine.ext.webapp import template

from apps.app.models import App
from apps.client.models import Client
from apps.client.shopify.models import ClientShopify
from apps.gae_bingo.gae_bingo import ab_test, bingo
from apps.link.models import Link
from apps.product.models import Product
from apps.product.shopify.models import ProductShopify
from apps.sibt.actions import *
from apps.sibt.models import SIBT, SIBTInstance, PartialSIBTInstance
from apps.sibt.shopify.models import SIBTShopify
from apps.user.models import User
from apps.wosib.models import WOSIB

from util.consts import *
from util.helpers import *
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
        fb_app_id = SHOPIFY_APPS['SIBTShopify']['facebook']['app_id']
        page_url = self.request.get('url') or \
                   self.request.get('target_url') or \
                   self.request.headers.get('referer')
        product = None
        product_images = []

        # because of how Model.get() works, products _might_ also work if you
        # supply a product's Shopify ID (if applicable).
        product_uuids = self.request.get('products', '').split(',')

        # Store registration url (with backup options if it's missing)
        store_url = self.request.get('store_url') or page_url

        if not store_url:
            logging.error("store_url not found in ask.html query string!")

        product = product_shopify = None
        try:
            url_parts = urlparse(store_url)
            # all db entries are currently http; makes sure https browsers
            # can also get app.
            store_domain = "http://%s" % url_parts.netloc
            # store_domain = "%s://%s" % (url_parts.scheme, url_parts.netloc)

            # warning: parsing an empty string will give you :// without error
        except Exception, e:
            logging.error('error parsing referer %s' % e, exc_info=True)

        app = SIBT.get_by_store_url(store_domain)
        if not app:
            logging.error("Could not find SIBT app for %s" % store_domain)
            self.response.out.write("Please register at http://rf.rs/s/shopify/beta to use this product.")
            return
        elif not hasattr(app, 'client'):
            logging.error("SIBT app has no client.  Probably uninstall.")
            self.response.out.write("Please register at http://rf.rs/s/shopify/beta to use this product.")
            return
        else:
            logging.info("Found SIBT app %r" % app)

        # We should absolutely have a user here, but they could have blocked their cookies
        user = User.get(self.request.get('user_uuid'))
        user_found = 1 if hasattr(user, 'fb_access_token') else 0
        user_is_admin = user.is_admin() if isinstance(user , User) else False

        product_uuid = self.request.get('product_uuid', None) # optional
        product_shopify_id = self.request.get('product_shopify_id', None) # optional
        logging.debug("Product information: %r" % [product_uuid, product_shopify_id])

        # successive steps to obtain the product using any way possible
        try:
            # get this page's product
            logging.info("Getting product information by url")
            product = Product.get_or_fetch(page_url, app.client)
            logging.debug("product.get_or_fetch from URL, got %r" % product)

            products = [Product.get(uuid) for uuid in product_uuids]
            logging.debug("getting products by UUID, got %r" % product)

            if not products[0]:
                # maybe if product UUIDs are missing
                # (happens if cookies are disabled)
                products = [product]

            if not products[0]:
                # we failed to find a single product!
                raise LookupError
        except LookupError:
            # adandon the rest of the script, because we NEED a product!
            logging.error("Could not find products %r" % product_uuids)
            self.response.out.write("Products requested are not in our database yet.")
            return

        # compile list of product images (one image from each product)
        try:
            product_images = [getattr(prod, 'images')[0] for prod in products]
            logging.debug("product images: %r" % product_images)
        except IndexError:
            logging.debug("product has no images")
            product_images = ['']

        if not page_url: # if somehow it's still missing, fix the missing url
            page_url = product.resource_url

        # Store 'Show' action
        if user_found:
            SIBTShowingAskIframe.create(user, url=page_url, app=app) # Requires user

        # Fix the product description
        try:
            ex = '[!\.\?]+'
            productDesc = strip_html(product.description)
            parts = re.split(ex, productDesc[:150])
            if len(parts) > 1:
                productDesc = '.'.join(parts[:-1])
            else:
                productDesc = '.'.join(parts)
            if productDesc[:-1] not in ex:
                productDesc += '.'
        except Exception, e:
            productDesc = ''
            logging.warn('Probably no product description: %s' % e,
                         exc_info=True)

        # Make a new Link.
        # we will be replacing this target url with the vote page url once
        # we get an instance.
        origin_domain = os.environ.get('HTTP_REFERER', 'UNKNOWN')
        link = Link.create(page_url, app, origin_domain, user)

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
            'URL': URL,

            'app_uuid': app.uuid,
            'user_uuid': self.request.get('user_uuid', ''),
            'target_url': page_url,
            'store_domain': store_domain,

            'user_email': user.get_attr('email') if user_found else None,
            'user_name': user.get_full_name() if user_found else None,
            'user_pic': user.get_attr('pic') if user_found else None,

            'FACEBOOK_APP_ID': fb_app_id,
            'fb_redirect': "%s%s" % (URL, url('ShowFBThanks')),
            'user_has_fb_token': user_found,

            'products': quoted_join(product_uuids),
            'product_uuid': products[0].uuid,  # deprecated
            'product_title': products[0].title or "",
            'product_images': product_images,
            'product_desc': productDesc,

            'share_url': link.get_willt_url(),
            'willt_code': link.willt_url_code,

            'AB_share_text': ab_opt,
            'incentive_enabled': app.incentive_enabled,
        }

        path = os.path.join('apps/sibt/templates/', 'ask.html')

        self.response.headers.add_header('P3P', P3P_HEADER)
        self.response.out.write(template.render(path, template_values))
        return


class VoteDynamicLoader(URIHandler):
    """ Serves a plugin where people can vote on a purchase

    On v10 and up (standalone vote page), "voter is never asker"
    """
    def get(self):
        app = None
        instance_uuid = self.request.get('instance_uuid')
        link = None
        target = get_target_url(self.request.get('url'))
        template_values = {}
        user = User.get(self.request.get('user_uuid'))
        willt_code = self.request.get('willt_code')

        # successive stages to get instance
        try:
            # stage 1: get instance by instance_uuid
            instance = SIBTInstance.get_by_uuid(instance_uuid)

            # stage 2: get instance by willet code in URL
            if not instance and willt_code:
                logging.info('trying to get instance for code: %s' % willt_code)
                link = Link.get_by_code(willt_code)
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
                raise ValueError("No SIBT instance could be found!")

            # start looking for instance info
            if not app:
                app = instance.app_

            if not user and app:
                user = User.get_or_create_by_cookie (self, app)

            name = instance.asker.get_full_name()

            if not link:
                link = instance.link
            share_url = link.get_willt_url()

            # record that the vote page was once opened.
            SIBTShowingVote.create(user = user, instance = instance)
            event = 'SIBTShowingVote'

            # In the case of a Shopify product, it will fetch from a .json URL.
            product = Product.get_or_fetch(instance.url, app.client)

            try:
                product_img = product.images[0]
            except:
                product_img = ''

            yesses = instance.get_yesses_count()
            nos = instance.get_nos_count()
            try:
                percentage = yesses / float (yesses + nos)
            except ZeroDivisionError:
                percentage = 0.0 # "it's true that 0% said buy it"

            template_values = {
                    'evnt' : event,
                    'product': product,
                    'product_img': product_img,
                    'app' : app,
                    'URL': URL,

                    'user': user,
                    'asker_name' : name if name else "your friend",
                    'asker_pic' : instance.asker.get_attr('pic'),
                    'target_url' : target,
                    'fb_comments_url' : '%s' % (link.get_willt_url()),
                    'percentage': percentage,
                    'share_url': share_url,
                    'product_url': product.resource_url,
                    'store_url': app.store_url,
                    'store_name': app.store_name,
                    'instance' : instance,
                    'votes': yesses + nos,
                    'yesses': instance.get_yesses_count(),
                    'noes': instance.get_nos_count()
            }

            path = os.path.join('apps/sibt/templates/', 'vote.html')

        except ValueError:
            # We can't find the instance, so let's assume the vote is over
            template_values = {
                'output': 'Vote is over'
            }
            path = os.path.join('apps/sibt/templates/', 'close_iframe.html')

        # Finally, render the HTML!
        self.response.headers.add_header('P3P', P3P_HEADER)
        self.response.out.write(template.render(path, template_values))
        return


class ShowResults(URIHandler):
    """Shows the results of a 'Should I Buy This?'"""
    def get(self):
        template_values = {}
        user = User.get(self.request.get('user_uuid'))
        target = get_target_url(self.request.get('url'))
        link = app = None

        # successive stages to get instance
        try:
            # stage 1: get instance by instance_uuid
            instance = SIBTInstance.get_by_uuid(self.request.get('instance_uuid'))

            # stage 2: get instance by willet code in URL
            if not instance and self.request.get('willt_code'):
                logging.info('trying to get instance for code: %s' % \
                              self.request.get('willt_code'))
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
                raise ValueError("Tried everything - no SIBT instance could be found!")

            # start looking for instance info
            if not app:
                app = instance.app_

            if not user and app:
                user = User.get_or_create_by_cookie (self, app)

            name = instance.asker.get_full_name()

            # we get these values before we submit the results
            # because we cannot be sure how quickly the taskqueue will finish
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
                event = 'SIBTShowingResultsToFriend'
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
                'instance' : instance,
                'instance_ends': '%s%s' % (instance.end_datetime.isoformat(), 'Z'),

                'vote_percentage': vote_percentage,
                'total_votes' : total
            }

            # Finally, render the HTML!
            path = os.path.join('apps/sibt/templates/', 'results.html')

        except ValueError:
            # well, we can't find the instance, so let's assume the vote is over
            self.response.out.write("The vote is over.")
            return

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
            except AttributeError, e:
                logging.error ("partial is: %s (%s)" % (partial, e))

            try:
                product_image = product.images[0]
            except:
                product_image = '%s/static/imgs/blank.png' % URL # blank

            # Make the Instance!
            instance = app.create_instance(user, None, link, product_image,
                                           motivation=None, dialog="NoConnectFB")

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
        app = None
        app_css = ''
        asker_name = ''
        asker_pic = ''
        event = 'SIBTShowingButton'
        instance = None
        is_asker = False
        is_live = False
        is_safari = False
        link = None
        page_url = self.request.get('url', self.request.get('page_url', ''))
        parts = {}
        product = None
        show_top_bar_ask = False
        store_url = self.request.get('store_url')
        template_values = {}
        unsure_mutli_view = False
        user = None
        votes_count = 0
        willet_code = self.request.get('willt_code')

        page_url = page_url.split('#')[0]  # clean up window.location
        if not page_url:
            # serve comment instead of status code (let customers see it)
            self.response.out.write('/* missing URL */')
            return

        if not store_url:
            # try to get store_url from page_url
            logging.warn("store is requsting scripting with its page URL "
                         "(does not work for extra_urls)")
            parts = urlparse(page_url)
            if parts.scheme and parts.netloc:
                store_url = '%s://%s' % (parts.scheme, parts.netloc)
            else:
                self.response.out.write('/* malformed URL */')
                return

        try:  # raises KindError both when decode fails and when app is absent
            # check if site is Shopify; get the Shopify app if possible
            app = SIBTShopify.get_by_store_url(store_url)
            if not app:
                raise db.KindError("don't have SIBTShopify for site")
        except db.KindError:
            logging.debug('This domain does not have a SIBTShopify app. '
                          'Trying to get SIBT app.')
            # if site is not Shopify, use the SIBT app
            app = SIBT.get_by_store_url(store_url)

        if app:  # got_by_store_url
            client = app.client
            if not client:
                return  # this app is not installed.
            logging.info('using %r and %r as app and client.' % (app, client))
        else:
            logging.debug('This domain does not have a SIBT app, either.'
                          'Getting client to check what apps it has installed')

            try:
                # first try get the Shopify client if one exists
                client = ClientShopify.get_by_url(store_url)
                if not client:
                    raise db.KindError("don't have ClientShopify for site")
            except db.KindError:
                client = Client.get_by_url(store_url)

            if client:
                # try to get existing SIBT/SIBTShopify from this client.
                # if not found, create one.
                # we can create one here because this implies the client had
                # never uninstsalled our app.
                app = SIBT.get_or_create(client=client, domain=store_url)
            else:  # we have no business with you
                self.response.out.write('/* no account for %s! '
                                        'Go to http://rf.rs to get an account. */' % store_url)
                return

        # not used until multi-ask is initiated
        app_wosib = WOSIB.get_or_create(client=app.client,domain=app.store_url)
        logging.debug("app_wosib = %r" % app_wosib)

        # have client, app
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
        # have client, app, user

        product = Product.get_or_fetch(page_url, client)

        # have client, app, user, and maybe product
        instance = SIBTInstance.get_by_asker_for_url(user, page_url)
        if not instance and willet_code:
            link = Link.get_by_code(willet_code)
            if link:
                instance = link.sibt_instance.get()

        if instance:
            event = 'SIBTShowingResults'
            asker_name = instance.asker.get_first_name() or "your friend"
            asker_pic = instance.asker.get_attr('pic') or ''
            votes_count = bool(instance.get_yesses_count() +
                               instance.get_nos_count()) or 0
            is_asker = bool(instance.asker.key() == user.key())

        # unsure detection
        if not instance and app:
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
        logging.debug('%r' % [user, page_url, instance])

        try:
            app_css = app.get_css()  # only Shopify apps have CSS
        except AttributeError:
            app_css = ''  # it was not a SIBTShopify

        # indent like this: http://stackoverflow.com/questions/6388187
        template_values = {
            # general things
            'debug': APP_LIVE_DEBUG,
            'URL': URL,

            # store info
            'client': client,
            'page_url': page_url,  # current page
            'store_url': store_url,  # registration url
          # 'store_id': getattr(app, 'store_id', ''),

            # app info
            'app': app, # if missing, django omits these silently
            'app_css': app_css, # SIBT-JS does not allow custom CSS.
            'detect_shopconnection': True,
            'sibt_version': app.version or App.CURRENT_INSTALL_VERSION,

            # instance info
            'instance': instance,
            'evnt': event,
            'has_results': bool(votes_count > 0),
            'is_live': is_live,
            'show_top_bar_ask': show_top_bar_ask and app.top_bar_enabled,
            'show_votes': False, # this is annoying if True

            # product info
            'product': product,

            # user info
            'user': user,
            'asker_name': asker_name,
            'asker_pic': asker_pic,
            'is_asker': is_asker,
            'unsure_mutli_view': unsure_mutli_view,

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
