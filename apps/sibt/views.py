#!/usr/bin/env python

__author__ = "Willet, Inc."
__copyright__ = "Copyright 2012, Willet, Inc"

import logging
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
        """Shows the SIBT Ask page.

        params:
            url (required): the product URL; typically window.location.href

            user_uuid (optional)
            product_uuid (optional)
            product_shopify_id (optional)
        """
        page_url = self.request.get('url', self.request.headers.get('referer'))
        product = product_shopify = None
        try:
            url_parts = urlparse(page_url)
            store_domain = "%s://%s" % (url_parts.scheme, url_parts.netloc)
            # warning: parsing an empty string will give you :// without error
        except Exception, e:
            logging.error('error parsing referer %s' % e, exc_info = True)
        
        app = SIBT.get_by_store_url(store_domain)
        if not app:
            logging.error("could not find SIBT app for %s" % store_domain)
            self.response.out.write("Please register at http://rf.rs to use this product.")
            return

        user = User.get(self.request.get('user_uuid'))
        user_found = 1 if hasattr(user, 'fb_access_token') else 0
        user_is_admin = user.is_admin() if isinstance(user , User) else False
        
        product_uuid = self.request.get('product_uuid', None) # optional
        product_shopify_id = self.request.get('product_shopify_id', None) # optional
        logging.debug("%r" % [product_uuid, product_shopify_id])

        # successive steps to obtain the product using any way possible
        try:
            logging.info("getting by url")
            product = Product.get_or_fetch (page_url, app.client) # by URL
            if not product and product_uuid: # fast (cached)
                product = Product.get (product_uuid)
            if not product and product_shopify_id: # slow, deprecated
                product_shopify = ProductShopify.get_by_shopify_id (product_shopify_id)
            if not product: # last resort: assume site is Shopify, and hit (product url).json
                product_shopify = ProductShopify.get_or_fetch(url=page_url,
                                                              client=app.client)

            # if we used a Shopify method, reget this product by its uuid so we get the non-shopify object
            if product_shopify:
                product = Product.get(product_shopify.uuid)
            
            if not product:
                # we failed to find a single product!
                raise LookupError
        except LookupError:
            # adandon the rest of the script, because we NEED a product!
            self.response.out.write("Product on this page is not in our database yet. <br /> \
                Please specify a product on your page with a div class=_willet_sibt element.")
            return

        if not page_url: # if somehow it's still missing, fix the missing url
            page_url = product.resource_url

        # Store 'Show' action
        SIBTShowingAskIframe.create(user, url=page_url, app=app)
        
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
            logging.warn('Probably no product description: %s' % e, exc_info=True)

        # Make a new Link
        origin_domain = os.environ['HTTP_REFERER'] if\
            os.environ.has_key('HTTP_REFERER') else 'UNKNOWN'
        
        # we will be replacing this target url with the vote page url once we get an instance.
        link = Link.create(page_url, app, origin_domain, user)
        
        # Which share message should we use?
        ab_share_options = [ 
            "I'm not sure if I should buy this. What do you think?",
            "Would you buy this? I need help making a decision!",
            "I need some shopping advice. Should I buy this? Would you?",
            "Desperately in need of some shopping advice! Should I buy this? Would you? Vote here.",
        ]
        
        if not user_is_admin:
            ab_opt = ab_test('sibt_share_text3',
                              ab_share_options,
                              user = user,
                              app = app)
        else:
            ab_opt = "ADMIN: Should I buy this? Please let me know!"

        template_values = {
            'URL': URL,

            'app_uuid': app.uuid,
            'user_uuid': self.request.get('user_uuid'),
            'target_url': page_url,
            'store_domain': store_domain,

            'user_email': user.get_attr('email') if user_found else None,
            'user_name': user.get_full_name() if user_found else None,
            'user_pic': user.get_attr('pic') if user_found else None,

            'FACEBOOK_APP_ID': SHOPIFY_APPS['SIBTShopify']['facebook']['app_id'], # doesn't actually involve Shopify
            'fb_redirect': "%s%s" % (URL, url('ShowFBThanks')),
            'user_has_fb_token': user_found,

            'product_uuid': product.uuid,
            'product_title': product.title if product else "",
            'product_images': product.images if product and len(product.images) > 0 else [],
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
                if not has_voted:
                    if doing_vote:
                        # the user wanted to vote too
                        if vote_result:
                            vote_result = 'yes'
                            yesses += 1
                        else:
                            vote_result = 'no'
                            noes += 1

                        taskqueue.add(
                            url = url('DoVote'),
                            params = {
                                'which': vote_result,
                                'user_uuid': user.uuid,
                                'instance_uuid': instance.uuid
                            }
                        )
                        has_voted = True

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
            template_values = {
                'output': 'Vote is over'        
            }
            path = os.path.join('apps/sibt/templates/', 'close_iframe.html')

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

        Required params: url (the page URL)
        Optional params: willt_code (helps find instance)
        """
        # declare vars.
        app = None
        app_css = ''
        asker_name = ''
        asker_pic = ''
        domain = ''
        event = 'SIBTShowingButton'
        instance = None
        is_asker = False
        is_live = False
        is_safari = False
        link = None
        parts = {}
        path = ''
        product = None
        show_top_bar_ask = False
        template_values = {}
        unsure_mutli_view = False
        user = None
        votes_count = 0

        # in the proposed SIBT v10, page URL is the only required parameter
        page_url = self.request.get('url', '').split('#')[0]
        if not page_url:
            # serve comment instead of status code (let customers see it)
            self.response.out.write('/* missing URL */')
            return

        try:
            parts = urlparse(page_url)
            domain = '%s://%s' % (parts.scheme, parts.netloc)
            path = parts.path
        except:
            self.response.out.write('/* malformed URL */')
            return

        try:  # raises KindError both when decode fails and when app is absent
            # check if site is Shopify; get the Shopify app if possible
            app = SIBTShopify.get_by_store_url(domain)
            if not app:
                raise db.KindError("don't have SIBTShopify for site")
        except db.KindError:
            logging.debug('This domain does not have a SIBTShopify app. '
                          'Trying to get SIBT app.')
            # if site is not Shopify, use the SIBT app
            app = SIBT.get_by_store_url(domain)

        if app:
            client = app.client
            if not client:
                return  # this app is not installed.
            logging.info('using %r and %r as app and client.' % (app, client))
        else:
            logging.debug('This domain does not have a SIBT app, either.'
                          'Getting client to check what apps it has installed')

            try:
                # first try get the Shopify client if one exists
                client = ClientShopify.get_by_url(domain)
                if not client:
                    raise db.KindError("don't have ClientShopify for site")
            except db.KindError:
                client = Client.get_by_url(domain)

            if client:
                # try to get existing SIBT/SIBTShopify from this client.
                # if not found, create one.
                apps = [a for a in client.apps if a.class_name() == 'SIBTShopify']
                if apps:
                    app = apps[0]

                if not app:
                    # if client exists and the app is not installed for it,
                    # automatically install the app for the client
                    logging.debug('no SIBTShopify for client')
                    '''
                    This does not work - ButtonsShopify token doesn't work
                    with SIBTShopify api keys. Re-enable on one-auth.

                    if client.class_name() == 'ClientShopify':
                        logging.debug('creating SIBTShopify')
                        # also installs webhooks and fetches products on create
                        app = SIBTShopify.get_or_create(client,
                                                        token=client.token,
                                                        email_client=False)
                    else:
                    '''
                    logging.debug('creating SIBT')
                    app = SIBT.get_or_create(client=client, domain=domain)
            else:  # we have no business with you
                self.response.out.write('/* no account for %s! '
                                        'Go to http://rf.rs to get an account. */' % domain)
                return

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
                if domain not in app.store_url:
                    # save the alternative URL so it can be called back later.
                    app.extra_url = domain
                    logging.info ("[SIBT] associating a new URL, %s, "
                                  "with the original, %s" % (app.extra_url,
                                                             app.store_url))
                    app.put()
            except:
                pass  # can't decode target as URL; oh well!

        user = User.get_or_create_by_cookie(self, app)
        # have client, app, user

        product = Product.get_by_url(page_url)

        # have client, app, user, and maybe product
        instance = SIBTInstance.get_by_asker_for_url(user, page_url)
        willet_code = self.request.get('willt_code')
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

        is_safari = 'safari' in self.get_browser() and not \
                    'chrome' in self.get_browser()

        # indent like this: http://stackoverflow.com/questions/6388187
        template_values = {
            # general things
            'debug': APP_LIVE_DEBUG,
            'URL': URL,
            'PAGE': page_url,
            'DOMAIN': domain,
            'is_safari': is_safari,

            # store info
            'store_domain': domain, # legacy alias for DOMAIN?
            'store_url': page_url, # legacy alias for PAGE?
            'store_id': getattr(app, 'store_id', ''),
            'client': client,

            # app info
            'app': app, # if missing, django omits these silently
            'sibt_version': app.version or App.CURRENT_INSTALL_VERSION,
            'stylesheet': '../../plugin/templates/css/colorbox.css',
            'popup_stylesheet': '../../plugin/templates/css/popup.css',
            'app_css': app_css, # SIBT-JS does not allow custom CSS.
            'detect_shopconnection': True,

            # instance info
            'instance': instance,
            'evnt': event,
            'has_results': bool(votes_count > 0),
            'show_top_bar_ask': show_top_bar_ask and app.top_bar_enabled,
            'is_live': is_live,
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
