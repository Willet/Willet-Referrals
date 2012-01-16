#!/usr/bin/env python

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc"

import re, urllib

from django.utils               import simplejson as json
from google.appengine.api       import urlfetch
from google.appengine.api       import memcache
from google.appengine.api       import taskqueue 
from google.appengine.ext       import webapp
from google.appengine.ext.webapp      import template
from google.appengine.ext.webapp.util import run_wsgi_app
from time                       import time
from urlparse                   import urlparse

from apps.sibt.actions          import *
from apps.app.models            import *
from apps.gae_bingo.gae_bingo   import ab_test
from apps.gae_bingo.gae_bingo   import bingo
from apps.client.shopify.models import *
from apps.link.models           import Link
from apps.link.models           import create_link
from apps.link.models           import get_link_by_willt_code
from apps.order.models          import *
from apps.product.shopify.models import ProductShopify
from apps.sibt.models           import SIBTInstance
from apps.sibt.models           import PartialSIBTInstance
from apps.sibt.shopify.models   import SIBTShopify
from apps.sibt.shopify.models   import get_sibt_shopify_app_by_store_id, get_sibt_shopify_app_by_store_url
from apps.stats.models          import Stats
from apps.user.models           import User
from apps.user.models           import get_user_by_cookie

from util.consts                import *
from util.helpers               import *
from util.urihandler            import URIHandler
from util.strip_html import strip_html

class AskDynamicLoader(webapp.RequestHandler):
    """When requested serves a plugin that will contain various functionality
       for sharing information about a purchase just made by one of our clients"""
    
    # TODO: THis code is Shopify specific. Refactor.
    def get(self):
        template_values = {}
            
        user   = User.get(self.request.get('user_uuid'))
        app    = SIBTShopify.get_by_store_url(self.request.get('store_url'))
        target = get_target_url(self.request.get('url'))

        logging.debug('target: %s' % target)
        logging.info("APP: %r" % app)
        
        # if this is a topbar ask
        is_topbar_ask = (self.request.get('is_topbar_ask') != '') 

        origin_domain = os.environ['HTTP_REFERER'] if\
            os.environ.has_key('HTTP_REFERER') else 'UNKNOWN'
        
        logging.debug('target: %s' % target)

        logging.info("APP: %r" % app)

        # Grab the product info
        product = ProductShopify.get_or_fetch(target, app.client)

        # Make a new Link
        link = Link.create(target, app, origin_domain, user)
        user_is_admin = user.is_admin()
        
        # GAY BINGO
        if not user_is_admin:
            if app.incentive_enabled:
                bingo( 'sibt_incentive_text' )
            else:    
                bingo( 'sibt_button_text6' )
            
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
                              app  = app )
        else:
            ab_opt = "ADMIN: Should I buy this? Please let me know!"

        # Now, tell Mixpanel
        if is_topbar_ask:
            #app.storeAnalyticsDatum( 'SIBTShowingTBAskIframe', user, target )
            SIBTShowingAskTopBarIframe.create(user, url=target, app=app)
        else:
            #app.storeAnalyticsDatum( 'SIBTShowingAskIframe', user, target )
            SIBTShowingAskIframe.create(user, url=target, app=app)

        # User stats
        user_email = user.get_attr('email') if user else ""
        user_found = True if hasattr(user, 'fb_access_token') else False

        store_domain = ''
        try:
            page_url = urlparse(self.request.headers.get('referer'))
            store_domain   = "%s://%s" % (page_url.scheme, page_url.netloc)
        except Exception, e:
            logging.error('error parsing referer %s' % e)
            store_domain = self.request.get('store_url')

        try:
            #parts = product.description[:150].split('.')
            #logging.info('got parts: %s' % parts)
            #parts = parts[:-1]
            #logging.info('got off last bit: %s' % parts)
            #productDesc = '.'.join(parts) + '.'
            
            ex = '[!\.\?]+'
            #logging.info('before strip html: %s' % product.description)
            productDesc = strip_html(product.description)
            #logging.info('stripped of html: %s' % productDesc)
            parts = re.split(ex, productDesc[:150])
            #logging.info('parts: %s' % parts)
            if len(parts) > 1:
                productDesc = '.'.join(parts[:-1])
            else:
                productDesc = '.'.join(parts)
            #logging.info('cut last part: %s' % productDesc)
            if productDesc[:-1] not in ex:
                productDesc += '.'
                        
        except Exception,e:
            productDesc = ''
            logging.warn('Probably no product description: %s' % e, exc_info=True)

        template_values = {
            'product_uuid' : product.uuid,
            'productImg'   : product.images[0], 
            'productName'  : product.title, 
            'productDesc'  : productDesc,
            'product_id'   : product.shopify_id,
            'productURL'   : store_domain,

            'FACEBOOK_APP_ID': app.settings['facebook']['app_id'],
            'app': app,
            'willt_url': link.get_willt_url(),
            'willt_code': link.willt_url_code,

            'target_url' : target,
            
            'user': user,
            'user_email': user_email,
            'user_found': str(user_found).lower(),
            'AB_share_text' : ab_opt
        }

        # Finally, render the HTML!
        path = os.path.join('apps/sibt/templates/', 'ask.html')

        self.response.headers.add_header('P3P', P3P_HEADER)
        self.response.out.write(template.render(path, template_values))
        return

class PreAskDynamicLoader(webapp.RequestHandler):
    """When requested serves a plugin that will contain various functionality
       for sharing information about a purchase just made by one of our clients"""
    
    # TODO: THis code is Shopify specific. Refactor.
    def get(self):
        store_domain  = self.request.get('store_url')
        app           = SIBTShopify.get_by_store_url(self.request.get('store_url'))
        user          = User.get(self.request.get('user_uuid'))
        user_found    = 1 if hasattr(user, 'fb_access_token') else 0
        user_is_admin = user.is_admin() if isinstance( user , User) else False
        target        = self.request.get( 'url' )
        
        # Store 'Show' action
        SIBTShowingAskIframe.create(user, url=target, app=app)

        # We need this stuff here to fill in the FB.ui stuff 
        # if the user wants to post on wall
        try:
            page_url = urlparse(self.request.headers.get('referer'))
            store_domain = "%s://%s" % (page_url.scheme, page_url.netloc)
        except Exception, e:
            logging.error('error parsing referer %s' % e)

        # Fix the product description
        product = ProductShopify.get_or_fetch(target, app.client)
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
                              app  = app )
        else:
            ab_opt = "ADMIN: Should I buy this? Please let me know!"

        template_values = {
            'URL' : URL,

            'app_uuid'     : app.uuid,
            'user_uuid'    : self.request.get( 'user_uuid' ),
            'target_url'   : self.request.get( 'url' ),
            'store_url'    : self.request.get( 'store_url' ),
            'store_domain' : self.request.get( 'store_url' ),

            'FACEBOOK_APP_ID': app.settings['facebook']['app_id'],
            'fb_redirect'    : "%s%s" % (URL, url( 'ShowFBThanks' )),
            'user_has_fb_token' : user_found,

            'product_uuid'   : product.uuid,
            'product_title'  : product.title if product else "",
            'product_images' : product.images if product else "",
            'product_desc'   : productDesc,

            'share_url'      : link.get_willt_url(),
            'willt_code'     : link.willt_url_code,

            'AB_share_text'  : ab_opt,
            'incentive_enabled' : app.incentive_enabled,
        }

        path = os.path.join('apps/sibt/templates/', 'preask.html')

        self.response.headers.add_header('P3P', P3P_HEADER)
        self.response.out.write(template.render(path, template_values))
        return


class VoteDynamicLoader(webapp.RequestHandler):
    """When requested serves a plugin that will contain various functionality
       for sharing information about a purchase just made by one of our clients"""
    def get(self):
        template_values = {}
        user   = User.get(self.request.get('user_uuid'))
        target = get_target_url(self.request.get('url'))
        link   = None
        app    = None

        instance = SIBTInstance.get_by_uuid(self.request.get('instance_uuid'))
        try:
            # get instance by instance_uuid
            assert(instance != None)
        except:
            try:
                # get instance by link
                # Grab the link

                # TODO: SHOPIFY IS DEPRECATING STORE_ID, USE STORE_URL INSTEAD
                logging.info('trying to get instance for code: %s' % self.request.get('willt_code'))
                app  = get_sibt_shopify_app_by_store_id(self.request.get('store_id'))
                link = get_link_by_willt_code(self.request.get('willt_code'))
                
                if link == None:
                    # no willt code, asker probably came back to page with
                    # no hash code
                    link = Link.all()\
                            .filter('user =', user)\
                            .filter('target_url =', target)\
                            .filter('app_ =', app)\
                            .get()
                    logging.info('got link by page_url %s: %s' % (target, link))
                instance = link.sibt_instance.get()
                assert(instance != None)
            except:
                try:
                    # get instance by asker
                    instance = SIBTInstance.get_by_asker_for_url(user, target)
                    assert(instance != None)
                except:
                    try:
                        # ugh, get the instance by actions ...
                        instances = SIBTInstance.all(key_onlys=True)\
                            .filter('url =', target)\
                            .filter('is_live =', True)\
                            .fetch(100)
                        key_list = [instance.id_or_name() for instance in instances]
                        action = SIBTClickAction.get_for_instance(app, user, target, key_list)
                        if action:
                            instance = action.sibt_instance
                            logging.info('no link, got action %s and instance %s' % (action, instance))
                        assert(instance != None)
                    except:
                        logging.error('failed to get instance', exc_info=True)

        logging.info("Did we get an instance? %s" % instance.uuid)
        
        if instance:
            if app == None:
                app = instance.app_

            name = instance.asker.get_full_name()
            is_asker = (instance.asker.key() == user.key())
            vote_action = SIBTVoteAction.get_by_app_and_instance_and_user(app, instance, user)
            
            logging.info('got vote action: %s' % vote_action)
            has_voted = (vote_action != None)
            if not instance.is_live:
                has_voted = True

            if link == None: 
                link = instance.link
            share_url = link.get_willt_url()

            if is_asker:
                SIBTShowingResultsToAsker.create(user=user, instance=instance)
                event = 'SIBTShowingResultsToAsker'
            elif has_voted:
                SIBTShowingResults.create(user=user, instance=instance)
                event = 'SIBTShowingResultsToFriend'
            else:
                SIBTShowingVote.create(user=user, instance=instance)


            # Now, tell Mixpanel
            # ... NOPE, I don't wanna!
            #app.storeAnalyticsDatum( event, user, target )

            product = ProductShopify.get_or_fetch(target, app.client)

            template_values = {
                    'evnt' : event,

                    'product_img': product.images,
                    'app' : app,
                    'URL': URL,
                    
                    'user': user,
                    'asker_name' : name if name != '' else "your friend",
                    'asker_pic' : instance.asker.get_attr('pic'),
                    'target_url' : target,
                    #'fb_comments_url' : '%s#code=%s' % (target, link.willt_url_code),
                    'fb_comments_url' : '%s' % (link.get_willt_url()),

                    'share_url': share_url,
                    'is_asker' : is_asker,
                    'instance' : instance,
                    'has_voted': has_voted,

                    'yesses': instance.get_yesses_count(),
                    'noes': instance.get_nos_count()
            }

            # Finally, render the HTML!
            path = os.path.join('apps/sibt/templates/', 'vote.html')
        else:
            event = 'SIBTEventOverClosingIframe'
            template_values = {
                'output': 'Vote is over'        
            }
            path = os.path.join('apps/sibt/templates/', 'close_iframe.html')

        self.response.headers.add_header('P3P', P3P_HEADER)
        self.response.out.write(template.render(path, template_values))
        return

class ShowResults(webapp.RequestHandler):
    """Shows the results of a 'should I buy this'"""
    def get(self):
        template_values = {}
        user   = User.get(self.request.get('user_uuid'))
        target = get_target_url( self.request.get('url') )

        doing_vote  = (self.request.get('doing_vote')  == 'true')
        vote_result = (self.request.get('vote_result') == 'true')
        
        link      = None
        app       = None
        has_voted = False

        instance = SIBTInstance.get_by_uuid(self.request.get('instance_uuid'))
        try:
            # get instance by instance_uuid
            assert(instance != None)
        except Exception, e:
            try:
                logging.info('failed to get instance by uuid: %s\n%s' % (
                            self.request.get('instance_uuid'), e))
                # get instance by link
                app = SIBTShopify.get_by_store_url(self.request.get('store_url'))
                code = self.request.get('willt_code')
                link = get_link_by_willt_code(code)
                
                if link == None:
                    # no willt code, asker probably came back to page with
                    # no hash code
                    link = Link.all()\
                            .filter('user =', user)\
                            .filter('target_url =', target)\
                            .filter('app_ =', app)\
                            .get()
                    logging.info('got link by page_url %s: %s' % (target, link))
                instance = link.sibt_instance.get()
                assert(instance != None)
            except Exception,e:
                try:
                    logging.info('failed to get instance by link: %s' % e)
                    # get instance by asker
                    instance = SIBTInstance.get_by_asker_for_url(user, target)
                    assert(instance != None)
                except Exception,e:
                    try:
                        # ugh, get the instance by actions ...
                        logging.info('failed to get instance for asker by url: %s' % e)
                        instances = SIBTInstance.all(keys_only=True)\
                            .filter('url =', target)\
                            .fetch(100)
                        key_list = [instance.id_or_name() for instance in instances]
                        action = SIBTClickAction.get_for_instance(app, user, target, key_list)
                        if action:
                            instance = action.sibt_instance.get()
                            logging.info('no link, got action %s and instance %s' % (action, instance))
                        assert(instance != None)
                    except Exception, e:
                        logging.error('failed to get instance: %s' % e, exc_info=True)

        logging.info("Did we get an instance? %s" % instance)
        event = 'SIBTShowingButton'
        
        if instance:
            if app == None:
                app = instance.app_
            
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

            # Now, tell Mixpanel
            #app.storeAnalyticsDatum(event, user, target)

            product = ProductShopify.get_or_fetch(target, app.client)

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
                'has_voted': has_voted,
                'is_live': instance.is_live,

                'vote_percentage': vote_percentage,
                'total_votes' : total
            }

            # Finally, render the HTML!
            path = os.path.join('apps/sibt/templates/', 'results.html')
        else:
            event = 'SIBTEventOverClosingIframe'
            template_values = {
                'output': 'Vote is over'        
            }
            path = os.path.join('apps/sibt/templates/', 'close_iframe.html')

        self.response.headers.add_header('P3P', P3P_HEADER)
        self.response.out.write(template.render(path, template_values))
        return

class ShowFBThanks( URIHandler ):
    """ Called to show fb_thanks.html. 
        We know the user jsut shared on FB, so create an instance etc. """

    # http://barbara-willet.appspot.com/s/fb_thanks.html?post_id=122604129_220169211387499#_=_
    def get( self ):
        email       = ""
        incentive_enabled = False
        user_cancelled = True
        app         = None
        post_id     = self.request.get( 'post_id' ) # from FB
        user        = get_user_by_cookie( self )
        partial     = PartialSIBTInstance.get_by_user( user )
        
        if post_id != "":
            user_cancelled = False

            # GAY BINGO
            if not user.is_admin():
                bingo( 'sibt_fb_no_connect_dialog' )
            
            # Grab stuff from PartialSIBTInstance
            app      = partial.app_
            link     = partial.link
            product  = partial.product

            # Make the Instance!

            try:
                product_image = product.images[0]
            except:
                product_image = '%s/static/imgs/blank.png' % URL # blank
            instance = app.create_instance(user, None, link, product_image,
                                           motivation=None, dialog="NoConnectFB")

            # increment link stuff
            link.app_.increment_shares()
            link.add_user(user)
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
