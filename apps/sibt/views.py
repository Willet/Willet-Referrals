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

from apps.action.models         import SIBTClickAction, SIBTVoteAction
from apps.action.models         import get_sibt_click_actions_by_user_and_link
from apps.app.models            import *
from apps.sibt.models           import get_sibt_instance_by_asker_for_url, SIBTInstance
from apps.sibt.shopify.models   import SIBTShopify
from apps.sibt.shopify.models   import get_sibt_shopify_app_by_store_id
from apps.link.models           import Link
from apps.link.models           import create_link
from apps.link.models           import get_link_by_willt_code
from apps.user.models           import User
from apps.user.models           import get_or_create_user_by_cookie
from apps.user.models           import get_user_by_cookie
from apps.client.models         import *
from apps.order.models          import *
from apps.stats.models          import Stats

from util.consts                import *
from util.helpers               import *
from util.urihandler            import URIHandler

class AskDynamicLoader(webapp.RequestHandler):
    """When requested serves a plugin that will contain various functionality
       for sharing information about a purchase just made by one of our clients"""
    
    # TODO: THis code is Shopify specific. Refactor.
    def get(self):
        template_values = {}
            
        origin_domain = os.environ['HTTP_REFERER'] if\
            os.environ.has_key('HTTP_REFERER') else 'UNKNOWN'
        
        page_url = urlparse( self.request.get('url') )
        target   = "%s://%s%s" % (page_url.scheme, page_url.netloc, page_url.path)
        if target == "://":
            target = "http://www.social-referral.appspot.com"

        # Grab a User and App
        user = get_or_create_user_by_cookie(self)
        # TODO: stop using store_id, use store_url
        app  = get_sibt_shopify_app_by_store_id(self.request.get('store_id'))
        logging.info("APP: %r" % app)

        # Grab the product info
        result = urlfetch.fetch(
            url = '%s.json' % self.request.get('url'),
            method = urlfetch.GET
        )
        data = json.loads( result.content )['product']

        # Make a new Link
        link = create_link(target, app, origin_domain, user)
        
        # User stats
        user_email = user.get_attr('email') if user else ""
        user_found = True if hasattr(user, 'fb_access_token') else False

        template_values = {
                'productImg'  : data['images'][0]['src'],
                'productName' : data['title'],
                'productDesc' : remove_html_tags( data['body_html'].strip() ),

                'FACEBOOK_APP_ID' : FACEBOOK_APP_ID,
                'app' : app,
                'willt_url' : link.get_willt_url(),
                'willt_code' : link.willt_url_code,
                
                'user': user,
                'user_email': user_email,
                'user_found': str(user_found).lower(),
        }

        taskqueue.add(
            queue_name = 'mixpanel', 
            url = '/mixpanel/action', 
            params = {
                'event'    : 'SIBTShowingAskIframe', 
                'app' : app.uuid,
                'user': user.get_name_or_handle(),
                'taret_url': target,
                'user_uuid': user.uuid,
                'user': user.get_name_or_handle(),
                'client': app.client.email
            }
        )

        # Finally, render the HTML!
        path = os.path.join('apps/sibt/templates/', 'ask.html')
        self.response.out.write(template.render(path, template_values))
        return

class VoteDynamicLoader(webapp.RequestHandler):
    """When requested serves a plugin that will contain various functionality
       for sharing information about a purchase just made by one of our clients"""
    def get(self):
        template_values = {}
        page_url = urlparse(self.request.get('url'))
        target   = "%s://%s%s" % (page_url.scheme, page_url.netloc, page_url.path)
        if target == "://":
            target = "http://www.social-referral.appspot.com"

        # Grab a User and App
        user = get_or_create_user_by_cookie(self)
        # TODO: SHOPIFY IS DEPRECATING STORE_ID, USE STORE_URL INSTEAD
        app  = get_sibt_shopify_app_by_store_id(self.request.get('store_id'))
       
        # Grab the link
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
        
        # Make sure User has a click action for this code
        actions = get_sibt_click_actions_by_user_and_link(user, target)
        asker_instance = get_sibt_instance_by_asker_for_url(user, target)
        # TODO: If no actions, this User didn't click on a link - THEY FAKED IT.
        logging.info('got action: %s' % actions)

        if link != None and link.sibt_instance.get() != None:
            instance = link.sibt_instance.get()
            logging.info('got instance from link')
        elif asker_instance != None:
            page_url = self.request.headers['REFERER']
            instance = asker_instance
            logging.info('got instance for asker')
        else:
            unfiltered_count = actions.count()
            instances = SIBTInstance.all()\
                .filter('url =', target)\
                .filter('is_live =', True)
            key_list = [instance.key() for instance in instances]
            actions = actions\
                    .filter('sibt_instance !=', '')\
                    .filter('sibt_instance IN', key_list)
            logging.info('got %d/%d actions after filtered by keys %s' % (
                actions.count(),
                unfiltered_count,
                key_list
            ))
            if actions.count() > 0:
                action = actions.get()
                instance = action.sibt_instance
                logging.info('no link, got action %s and instance %s' % (action, instance))

        logging.info("Did we get an instance? %s" % instance)
        
        # default event
        event = 'SIBTShowingVoteIframe'

        if instance.is_live:
            name = instance.asker.get_full_name()
            is_asker = (instance.asker.key() == user.key())
            vote_action = SIBTVoteAction.all()\
                    .filter('app_ =', app)\
                    .filter('sibt_instance =', instance)\
                    .filter('user =', user)\
                    .get()
            logging.info('got vote action: %s' % vote_action)
            has_voted = (vote_action != None)

            if is_asker:
                event = 'SIBTShowingResultsToAsker'
            elif has_voted:
                event = 'SIBTShowingResultsToFriend'
            
            link = instance.link
            share_url = '%s/%s' % (
                URL,
                link.willt_url_code
            )

            template_values = {
                    'product_img' : self.request.get( 'photo' ),
                    'app' : app,
                    'URL': URL,
                    
                    'user': user,
                    'asker_name' : name if name != '' else "your friend",
                    'asker_pic' : instance.asker.get_attr('pic'),
                    'fb_comments_url' : '%s/%s' % (target, instance.uuid),

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

        taskqueue.add(
            queue_name = 'mixpanel', 
            url = '/mixpanel/action', 
            params = {
                'event': event, 
                'app': app.uuid,
                'user': user.get_name_or_handle(),
                'user_uuid': user.uuid,
                'taret_url': target,
                'client': app.client.email
            }
        )

        self.response.out.write(template.render(path, template_values))
        return

