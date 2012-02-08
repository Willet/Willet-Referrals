#!/usr/bin/env python

__author__      = "Sy Khader"
__copyright__   = "Copyright 2011, The Willet Corporation"


import os, logging, urllib, simplejson

from google.appengine.api import taskqueue, urlfetch
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

# models
from apps.email.models import *
from apps.app.models import get_app_by_id
from apps.link.models import Link
from apps.user.models import get_user_by_cookie, get_or_create_user_by_email, get_or_create_user_by_facebook, get_user_by_uuid, get_or_create_user_by_cookie

# helpers
from apps.referral.shopify.api_wrapper import add_referrer_gift_to_shopify_order
from util.consts import *
from util.helpers import read_user_cookie, generate_uuid, get_request_variables

class SendEmailInvites( webapp.RequestHandler ):
    def post( self ):
        from_addr = self.request.get( 'from_addr' )
        to_addrs  = self.request.get( 'to_addrs' )
        msg       = self.request.get( 'msg' )
        url       = self.request.get( 'url' )
        order_id  = self.request.get( 'order_id' ) 
        willt_url_code = self.request.get( 'willt_url_code' )
        via_willet = True if self.request.get( 'via_willet' ) == 'true' else False
        
        logging.info("ASDSD %s %s %s" % (self.request.arguments(),willt_url_code, order_id))

        # check to see if this user has a referral cookie set
        referrer_code = self.request.cookies.get('referral', None)
        referrer = None
        logging.info(referrer_code)
        if referrer_code:
            referral_link = Link.get_by_code(referrer_code)
            if referral_link and referral_link.user:
                referrer = referral_link.user
        
        # Get the User
        user = get_or_create_user_by_email(from_addr, self, None)
        
        # Get the Link & update it
        link = Link.get_by_code(willt_url_code)
        if link:
            link.user = user
            link.email_sent = True
            link.put()
            
            for i in range(0, to_addrs.count(',')):
                link.app_.increment_shares()
                
            # If we are on a shopify store, add a gift to the order
            if link.app_.__class__.__name__.lower() == 'referralshopify':
                add_referrer_gift_to_shopify_order( order_id )

            # Send off the email if they don't want to use a webmail client
            if via_willet and to_addrs != '':
                Email.invite( infrom_addr=from_addr, to_addrs=to_addrs, msg=msg, url=url, app=link.app_)

        return

