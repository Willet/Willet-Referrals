#!/usr/bin/env python

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2012, Willet, Inc"

import datetime
import random

from datetime                         import datetime, timedelta
from django.utils                     import simplejson as json
from google.appengine.api             import taskqueue
from google.appengine.api             import memcache
from google.appengine.ext             import webapp
from google.appengine.ext             import db 
from google.appengine.ext.webapp      import template
from google.appengine.ext.webapp.util import run_wsgi_app
from time                             import time
from urlparse                         import urlparse

from apps.action.models               import ButtonLoadAction
from apps.action.models               import ScriptLoadAction
from apps.app.models                  import *
from apps.client.models               import *
from apps.gae_bingo.gae_bingo         import ab_test
from apps.link.models                 import Link
from apps.order.models                import *
from apps.product.shopify.models      import ProductShopify
from apps.sibt.shopify.models         import SIBTShopify
from apps.user.models                 import get_user_by_cookie
from apps.user.models                 import User
from apps.user.models                 import get_or_create_user_by_cookie
from apps.wosib.actions               import WOSIBVoteAction
from apps.wosib.models                import WOSIBInstance
from apps.wosib.shopify.models        import WOSIBShopify

from util.consts                      import *
from util.helpers                     import *
from util.shopify_helpers             import get_shopify_url
from util.urihandler                  import URIHandler

class WOSIBShopifyServeScript (webapp.RequestHandler):
    # chucks out a javascript that helps detect events and show wizards
    # (with wands and broomsticks)
    def get(self):
        votes_count = 0
        is_asker = show_votes = has_voted = show_top_bar_ask = False
        instance = share_url = link = asker_name = asker_pic = product = None
        instance_uuid = target   = bar_or_tab = ''
        willet_code = self.request.get('willt_code')
        shop_url    = get_shopify_url(self.request.get('store_url'))
        if not shop_url: # backup (most probably hit)
            shop_url    = get_target_url(self.request.headers.get('REFERER')) # probably ok
        logging.debug ("shop_url = %s" % shop_url)
        app         = WOSIBShopify.get_by_store_url(shop_url)
        app_sibt    = SIBTShopify.get_by_store_url(shop_url) # use its CSS and stuff
        event       = 'WOSIBShowingButton'

        target = get_target_url(self.request.headers.get('REFERER'))

        user = get_or_create_user_by_cookie( self, app )

        # Try to find an instance for this { url, user }
        try:
            logging.debug ("trying app = %s" % app)
            assert(app != None)
            try:
                # WOSIBInstances record the user. Find the user's most recent instance.
                logging.info('trying to get instance for user: %r' % user)
                instance = WOSIBInstance.get_by_user_and_app (user, app)
                assert(instance != None)
            except Exception, e:
                logging.info('no instance available: %s' % e)
        except:
            logging.info('no app')

        # If we have an instance, figure out if 
        # a) Is User asker?
        # b) Has this User voted?
        if instance:
            instance_uuid = instance.uuid
            
            # number of votes, not the votes objects.
            # votes_count = WOSIBVoteAction.all().filter('wosib_instance =', instance).count()
            votes_count = instance.get_votes_count() or 0
            logging.info ("votes_count = %s" % votes_count)
            
            asker_name = instance.asker.get_first_name()
            asker_pic  = instance.asker.get_attr('pic')
            show_votes = True

            try:
                asker_name = asker_name.split(' ')[0]
                if not asker_name:
                    asker_name = 'I' # what?
            except:
                logging.warn('error splitting the asker name')

            is_asker = (instance.asker.key() == user.key()) 
            if not is_asker:
                logging.info('not asker, check for vote ...')
                
                vote_action = WOSIBVoteAction.get_by_app_and_instance_and_user(app, instance, user)
                
                logging.info('got a vote action? %s' % vote_action)
                
                has_voted = (vote_action != None)

            try:
                if link == None: 
                    link = instance.link
                share_url = link.get_willt_url()
            except Exception,e:
                logging.error("could not get share_url: %s" % e, exc_info=True)

        else:
            logging.warn("no instance!")

        if not user.is_admin():
            cta_button_text = "Need advice? Ask your friends!"
        else:
            cta_button_text = "ADMIN: Unsure? Ask your friends!"
        
        # determine whether to show the button thingy.
        # code below makes button show only if vote was started less than 1 day ago.
        has_results = False
        if votes_count:
            time_diff = datetime.now() - instance.created
            if time_diff <= timedelta(days=1):
                has_results = True
        
        # Grab all template values
        template_values = {
            'URL'            : URL,
            'app'            : app,
            'app_css'        : app_sibt.get_css(),
            'instance'       : instance,
            'store_domain'   : getattr (app_sibt.client, 'domain', ''),
            'store_id'       : self.request.get('store_id'),
            'user'           : user,
            'instance_uuid'  : instance_uuid,
            'stylesheet'     : '../../plugin/templates/css/colorbox.css',
            'evnt'           : event,
            'cta_button_text': cta_button_text,
            'shop_url'       : shop_url,
            # this thing tells client JS if the user had created an instance
            'has_results'    : 'true' if has_results else 'false',
        }

        path = os.path.join('apps/wosib/templates/', 'wosib_button.js')
        self.response.headers.add_header('P3P', P3P_HEADER)
        self.response.headers['Content-Type'] = 'application/javascript'
        self.response.out.write(template.render(path, template_values))
        
        return
    
    def post (self):
        self.get() # because money.
