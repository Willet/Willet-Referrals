#!/usr/bin/env python

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2012, Willet, Inc"

import re
import hashlib
import urllib

from datetime                   import datetime, timedelta
from django.utils               import simplejson as json
from google.appengine.api       import urlfetch
from google.appengine.api       import memcache
from google.appengine.api       import taskqueue 
from google.appengine.ext       import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app
from time                       import time
from urlparse                   import urlparse

from apps.app.models            import *
from apps.client.shopify.models import *
from apps.gae_bingo.gae_bingo   import ab_test
from apps.gae_bingo.gae_bingo   import bingo
from apps.client.models         import *
from apps.client.shopify.models import *
from apps.link.models           import Link
from apps.order.models          import *
from apps.product.shopify.models import ProductShopify
from apps.sibt.actions          import *
from apps.sibt.models           import SIBT, SIBTInstance, PartialSIBTInstance
from apps.sibt.shopify.models   import SIBTShopify
from apps.user.models           import User

from util.consts                import *
from util.shopify_helpers       import get_shopify_url as format_url
from util.helpers               import *
from util.urihandler            import URIHandler
from util.strip_html            import strip_html

class ShowBetaPage(URIHandler):
    def get(self):
        path = os.path.join('apps/sibt/templates/', 'beta.html')
        self.response.out.write(template.render(path, {}))


class SIBTWelcome(URIHandler):
    # "install done" page. actually installs the apps.
    def get(self):
        path = os.path.join('apps/sibt/templates/', 'welcome.html')
        self.response.out.write(template.render(path, {}))


class AskDynamicLoader(webapp.RequestHandler):
    """Serves a plugin that will contain various functionality
       for sharing information about a purchase just made by one of our clients"""
    
    # TODO: THis code is Shopify specific. Refactor.
    def get(self):
        store_domain = self.request.get('store_url')
        app = SIBTShopify.get_by_store_url(store_domain)
        user = User.get(self.request.get('user_uuid'))
        user_found = 1 if hasattr(user, 'fb_access_token') else 0
        user_is_admin = user.is_admin() if isinstance( user , User) else False
        
        # if no URL, then referrer, then everything dies
        target = self.request.get ('url', self.request.headers.get('referer'))
        
        product_uuid = self.request.get( 'product_uuid', None ) # optional
        product_shopify_id = self.request.get( 'product_id', None ) # optional
        logging.debug("%r" % [product_uuid, product_shopify_id])

        # We need this stuff here to fill in the FB.ui stuff 
        # if the user wants to post on wall
        try:
            page_url = urlparse(self.request.headers.get('referer'))
            store_domain = "%s://%s" % (page_url.scheme, page_url.netloc)
        except Exception, e:
            logging.error('error parsing referer %s' % e, exc_info = True)
        
        # successive steps to obtain the product using any way possible
        try:
            logging.info("getting by url")
            product = ProductShopify.get_or_fetch (target, app.client) # by URL
            if not product and product_uuid: # fast (cached)
                product = ProductShopify.get (product_uuid)
                target = product.resource_url # fix the missing url
            if not product and product_shopify_id: # slow, deprecated
                product = ProductShopify.get_by_shopify_id (product_shopify_id)
                target = product.resource_url # fix the missing url
            if not product:
                # we failed to find a single product!
                raise LookupError
        except LookupError:
            # adandon the rest of the script, because we NEED a product!
            self.response.out.write("Requested product cannot be found.")
            return

        # Store 'Show' action
        SIBTShowingAskIframe.create(user, url=target, app=app)
        
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
        except Exception,e:
            productDesc = ''
            logging.warn('Probably no product description: %s' % e, exc_info=True)

        # Make a new Link
        origin_domain = os.environ['HTTP_REFERER'] if\
            os.environ.has_key('HTTP_REFERER') else 'UNKNOWN'
        
        # we will be replacing this target url with the vote page url once we get an instance.
        link = Link.create(target, app, origin_domain, user)
        
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
                              app = app )
        else:
            ab_opt = "ADMIN: Should I buy this? Please let me know!"

        template_values = {
            'URL' : URL,

            'app_uuid'     : app.uuid,
            'user_uuid'    : self.request.get( 'user_uuid' ),
            'target_url'   : self.request.get( 'url' ),
            'store_url'    : self.request.get( 'store_url' ),
            'store_domain' : self.request.get( 'store_url' ),

            'user_email'   : user.get_attr('email') if user_found else None,
            'user_name'    : user.get_full_name() if user_found else None,
            'user_pic'     : user.get_attr('pic') if user_found else None,

            'FACEBOOK_APP_ID': app.settings['facebook']['app_id'],
            'fb_redirect'    : "%s%s" % (URL, url( 'ShowFBThanks' )),
            'user_has_fb_token' : user_found,

            'product_uuid'   : product.uuid,
            'product_title'  : product.title if product else "",
            'product_images' : product.images if product and len(product.images) > 0 else [],
            'product_desc'   : productDesc,

            'share_url'      : link.get_willt_url(),
            'willt_code'     : link.willt_url_code,

            'AB_share_text'  : ab_opt,
            'incentive_enabled' : app.incentive_enabled,
        }

        path = os.path.join('apps/sibt/templates/', 'ask.html')

        self.response.headers.add_header('P3P', P3P_HEADER)
        self.response.out.write(template.render(path, template_values))
        return


class VoteDynamicLoader(webapp.RequestHandler):
    """ Serves a plugin where people can vote on a purchase
        On v4 and up (standalone vote page), "voter is never asker"
    """
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
                # TODO: SHOPIFY IS DEPRECATING STORE_ID, USE STORE_URL INSTEAD
                # app = SIBTShopify.get_by_store_id(self.request.get('store_id'))
                logging.info('trying to get instance for code: %s' % self.request.get('willt_code'))
                link = Link.get_by_code( self.request.get('willt_code') )
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
                raise ValueError ("Tried everything - no SIBT instance could be found!")

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

            product = ProductShopify.get_or_fetch(instance.url, app.client)
            
            try:
                product_img = product.images[0]
            except:
                product_img = ''
            
            yesses = instance.get_yesses_count()
            nos = instance.get_nos_count()
            try:
                percentage = yesses / float (yesses + nos)
            except ZeroDivisionError, e:
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

        except ValueError, e:
            # well, we can't find the instance, so let's assume the vote is over
            template_values = {
                'output': 'Vote is over'        
            }
            path = os.path.join('apps/sibt/templates/', 'close_iframe.html')

        # Finally, render the HTML!
        self.response.headers.add_header('P3P', P3P_HEADER)
        self.response.out.write(template.render(path, template_values))
        return


class ShowResults(webapp.RequestHandler):
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
                # TODO: SHOPIFY IS DEPRECATING STORE_ID, USE STORE_URL INSTEAD
                # app = SIBTShopify.get_by_store_id(self.request.get('store_id'))
                logging.info('trying to get instance for code: %s' % self.request.get('willt_code'))
                link = Link.get_by_code( self.request.get('willt_code') )
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
                raise ValueError ("Tried everything - no SIBT instance could be found!")

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
                has_voted = (vote_action != None)
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

            product = ProductShopify.get_or_fetch(instance.url, app.client)

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

        except ValueError, e:
            # well, we can't find the instance, so let's assume the vote is over
            template_values = {
                'output': 'Vote is over'        
            }
            path = os.path.join('apps/sibt/templates/', 'close_iframe.html')

        # Finally, render the HTML!
        self.response.headers.add_header('P3P', P3P_HEADER)
        self.response.out.write(template.render(path, template_values))
        return


class ShowFBThanks( URIHandler ):
    """ Called to show fb_thanks.html. 
        We know the user just shared on FB, so create an instance etc. """

    # http://barbara-willet.appspot.com/s/fb_thanks.html?post_id=122604129_220169211387499#_=_
    def get( self ):
        email = ""
        incentive_enabled = False
        user_cancelled = True
        app         = None
        post_id     = self.request.get( 'post_id' ) # from FB
        user        = User.get_by_cookie(self)
        partial     = PartialSIBTInstance.get_by_user( user )
        
        if post_id != "":
            user_cancelled = False

            # GAY BINGO
            if not user.is_admin():
                bingo( 'sibt_fb_no_connect_dialog' )
            
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
            link.target_url = "%s://%s%s?instance_uuid=%s" % (PROTOCOL, DOMAIN, url ('VoteDynamicLoader'), instance.uuid)
            logging.info ("link.target_url changed to %s (%s)" % (link.target_url, instance.uuid))

            # increment link stuff
            link.app_.increment_shares()
            link.add_user(user)
            link.put()
            link.memcache_by_code() # doubly memcached
            logging.info('incremented link and added user')
        elif partial != None:
            # Create cancelled action
            SIBTNoConnectFBCancelled.create( user, 
                                             url=partial.link.target_url,
                                             app=partial.app_ )

        if partial:
            # Now, remove the PartialSIBTInstance. We're done with it!
            partial.delete()

        template_values = { 'email'          : user.get_attr( 'email' ),
                            'user_cancelled' : user_cancelled,
                            'incentive_enabled' : app.incentive_enabled if app else False }
        
        path = os.path.join('apps/sibt/templates/', 'fb_thanks.html')
        self.response.headers.add_header('P3P', P3P_HEADER)
        self.response.out.write(template.render(path, template_values))
        return


class ColorboxJSServer( URIHandler ):
    """ Called to load Colorbox.js
    """
    def get( self ):
        template_values = { 'URL'           : URL,
                            'app_uuid'      : self.request.get('app_uuid'),
                            'user_uuid'     : self.request.get('user_uuid'),
                            'instance_uuid' : self.request.get('instance_uuid'),
                            'target_url'    : self.request.get('target_url') }
       
        path = os.path.join('apps/sibt/templates/js/', 'jquery.colorbox.js')
        self.response.headers.add_header('P3P', P3P_HEADER)
        self.response.out.write(template.render(path, template_values))
        return


class ShowOnUnloadHook( URIHandler ):
    ''' Creates a local-domain iframe that allows SJAX requests to be served
        when the window unloads. (Typically, webkit browsers do not complete 
        onunload functions unless a synchronous AJAX is sent onbeforeunload, and
        in order to send synced requests, the request must be sent to the same
        domain.)'''
    def get( self ):
        template_values = { 'URL'           : URL,
                            'app_uuid'      : self.request.get('app_uuid'),
                            'user_uuid'     : self.request.get('user_uuid'),
                            'instance_uuid' : self.request.get('instance_uuid'),
                            'target_url'    : self.request.get('target_url'),
                            'evnt'          : self.request.get('evnt')
                          }
        
        path = os.path.join('apps/sibt/templates/', 'onunloadhook.html')
        self.response.headers.add_header('P3P', P3P_HEADER)
        self.response.out.write(template.render(path, template_values))
        return

class SIBTGetUseCount (URIHandler):
    def get(self):
        # faking it for now. shows number of button loads divided by 100
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
    ''' Serves a script that shows the SIBT button.
        Due to the try-before-you-buy nature of the Internets, this view will
        not create a SIBT app for the store/domain until (undecided trigger).
        
        Example call: http://brian-willet.appspot.com/s/sibt.js?url=http%3A%2F%2Fkiehn-mertz3193.myshopify.com%2Fproducts%2Fcustomer-focused-leading-edge-algorithm
    '''
    
    def get(self):
        app = user = instance = None
        domain = path = ''
        parts = template_values = {}
        
        # in the proposed SIBT v10, page URL is the only required parameter.
        page_url = self.request.get ('url')
        if not page_url:
            self.response.out.write('/* missing URL */')
            return

        try:
            parts = urlparse(page_url) # http://docs.python.org/library/urlparse.html
            domain = '%s://%s' % (parts.scheme, parts.netloc)
            path = parts.path
        except:
            self.response.out.write('/* malformed URL */')
            return
        
        # app = SIBT.get(store_url=domain) # this get method does not work (yet)
        app = SIBT.get(hashlib.md5(domain).hexdigest()) # this, however, will
        client = Client.get_by_url(domain)
        if client and app:
            if client != app.client: # if something is really screwed up, fix it
                app.client = client
                app.put()
        elif client and not app:
            # if client exists and the app is not installed for it, then
            # automatically install the app for the client
            app = SIBT.get_or_create (
                client=client,
                domain=domain
            )
        elif not client:
            # we have no business with you
            self.response.out.write('/* no client for %s */' % domain)
            return
        
        user = User.get_or_create_by_cookie(self, app)

        instance = SIBTInstance.get_by_asker_for_url(user, page_url)
        # you now have app, user, client, and instance

        # indent like this: http://stackoverflow.com/questions/6388187
        template_values = {
            'URL': URL,
            'PAGE': page_url,
            'DOMAIN': domain,
            'app': app, # if missing, django omits these silently
            'user': user,
            'instance': instance,

            'stylesheet': '../../plugin/templates/css/colorbox.css',
            'sibt_version': app.version or App.CURRENT_INSTALL_VERSION,

            'is_asker': False,
            'show_votes': False,
            'has_voted': False,
            'has_results': False,
            'is_live': False,
            'unsure_mutli_view': False
        }
        
        path = os.path.join('apps/sibt/templates/', 'sibt_static.js')
        self.response.headers.add_header('P3P', P3P_HEADER)
        self.response.headers['Content-Type'] = 'text/javascript; charset=utf-8'
        self.response.out.write(template.render(path, template_values))
        return
    
    def post(self):
        self.get() # because money


