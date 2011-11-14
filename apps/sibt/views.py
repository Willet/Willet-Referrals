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

from apps.sibt.actions import *
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
from apps.sibt.shopify.models   import SIBTShopify
from apps.sibt.shopify.models   import get_sibt_shopify_app_by_store_id, get_sibt_shopify_app_by_store_url
from apps.stats.models          import Stats
from apps.user.models           import User

from util.consts                import *
from util.helpers               import *
from util.urihandler            import URIHandler

class AskDynamicLoader(webapp.RequestHandler):
    """When requested serves a plugin that will contain various functionality
       for sharing information about a purchase just made by one of our clients"""
    
    # TODO: THis code is Shopify specific. Refactor.
    def get(self):
        template_values = {}
            
        user   = User.get(self.request.get('user_uuid'))
        app    = get_sibt_shopify_app_by_store_url( self.request.get('store_url') )
        target = get_target_url( self.request.get('url') )
        logging.debug('target: %s' % target)
        logging.info("APP: %r" % app)
        
        # if this is a topbar ask
        is_topbar_ask = self.request.get('is_topbar_ask')
        is_topbar_ask = (is_topbar_ask != '') 

        origin_domain = os.environ['HTTP_REFERER'] if\
            os.environ.has_key('HTTP_REFERER') else 'UNKNOWN'
        
        logging.debug('target: %s' % target)

        logging.info("APP: %r" % app)

        # Grab the product info
        if app.client.uuid == 'e54825444acb4f2e': # ie. if doggie seat belt
            product = ProductShopify.get_by_shopify_id('48647062')
        else:
            product = ProductShopify.get_or_fetch(target, app.client)

        # Make a new Link
        link = create_link(target, app, origin_domain, user)
        
        # GAY BINGO
        if not user.is_admin():
            bingo( 'sibt_button_text4' )
            bingo( 'sibt_facebook_style' )

        ab_share_options = [ 
            "I'm not sure if I should buy this <input id='m_text' />. What do you think?",
            
            "Would you buy this <input id='m_text' />? I need help making a decision! Vote here:",
            
            "I need some shopping advice. Should I buy this <input id='m_text' />? Would you? More details here:",
            
            "Desperately in need of some shopping advice! Should I buy this <input id='m_text' />? Would you? Tell me here:",
        ]
        
        if not user.is_admin():
            ab_opt = ab_test('sibt_share_text2',
                              ab_share_options,
                              user = user,
                              app  = app )
        else:
            ab_opt = "Should I buy this <input id='m_text' />? Please let me know!"

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
            productDesc = '.'.join(product.description[:150].split('.')[:-1]) + '.'
        except Exception,e:
            productDesc = ''
            logging.warn('Probably no product description: %s' % e, exc_info=True)

        template_values = {
            'productImg' : product.images, 
            'productName': product.title, 
            'productDesc': productDesc,
            'product_id': product.shopify_id,
            'productURL': store_domain,

            #'FACEBOOK_APP_ID' : FACEBOOK_APP_ID,
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
        if is_topbar_ask:
            path = os.path.join('apps/sibt/templates/', 'ask_in_the_bar.html')
        else:
            path = os.path.join('apps/sibt/templates/', 'ask.html')

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
                            .filter('url =', url)\
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
        except:
            try:
                logging.info('failed to get instance by instance_uuid: %s' % instance_uuid)
                # get instance by link
                # Grab the link

                app  = get_sibt_shopify_app_by_store_url(self.request.get('store_url'))
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
                        instances = SIBTInstance.all(key_onlys=True)\
                            .filter('url =', url)\
                            .filter('is_live =', True)\
                            .fetch(100)
                        key_list = [instance.id_or_name() for instance in instances]
                        action = SIBTClickAction.get_for_instance(app, user, target, key_list)
                        if action:
                            instance = action.sibt_instance
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
                'has_voted': has_voted,
                'is_live': instance.is_live,

                'vote_percentage': vote_percentage
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

