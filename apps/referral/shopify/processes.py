#!/usr/bin/env python

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc"

import re, hashlib, urllib

from django.utils import simplejson as json
from google.appengine.api import urlfetch, memcache
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api.datastore_errors import BadValueError
from time import time

from apps.app.models import *
from apps.order.models import *
from apps.link.models import Link, get_link_by_willt_code
from apps.user.models import User, get_or_create_user_by_email, get_user_by_cookie
from apps.referral.shopify.models import get_shopify_app_by_id

from util.emails       import Email
from util.helpers import *
from util.urihandler import URIHandler
from util.consts import *
from util.gaesessions import get_current_session

class DoProcessOrder( URIHandler ):
    def post( self ):
        logging.info("HEADERS : %s %r" % (self.request.headers, self.request.headers ))
        # Grab the ShopifyApp
        store_id = self.request.get('store_id')
        logging.info("store: %s " %  store_id )
        app = get_shopify_app_by_id( store_id )

        # Grab the data about the order from Shopify
        order = json.loads( self.request.body ) #['orders'] # Fetch the order

        items = []
        order_id = token = order_num = referring_site = subtotal = None
        first_name = last_name = address1 = address2 = city = None
        province = country_code = postal_code = latitude = longitude = None
        phone = email = shopify_id = ip = accepts_marketing = None

        for k, v in order.iteritems():
            #logging.info("K: %s V: %s" % (k, v))
            
            # Grab order details
            if k == 'id':
                order_id = v
            elif k == 'subtotal_price':
                subtotal = v
            elif k == 'order_number':
                order_num = v
            elif k == 'referring_site':
                referring_site = v
            elif k == 'token':
                token = v
        
            # Grab the purchased items and save some information about them.
            elif k == 'line_items':
                for j in v:
                    i = ShopifyItem( name=str(j['name']), price=str(j['price']), product_id=str(j['product_id']))
                    items.append( i )

            # Store User/ Customer data
            elif k == 'billing_address':
                address1           = v['address1']
                address2           = v['address2']
                city               = v['city']
                province           = v['province']
                country_code       = v['country_code']
                postal_code        = v['zip']
                latitude           = v['latitude']
                longitude          = v['longitude']
                phone              = v['phone']
            elif k == 'email':
                email = v
            elif k == 'customer':
                first_name         = v['first_name']
                last_name          = v['last_name']
                shopify_id = v['id']
            elif k == 'browser_ip':
                ip = v
            elif k == 'buyer_accepts_marketing':
                accepts_marketing = v 
            elif k == 'landing_site':
                logging.info("LANDING SITE: %s" % v )

        # Check to see if this User has a referral cookie set
        referrer_code = self.request.cookies.get('referral', None)
        referrer = None
        logging.info(referrer_code)
        if referrer_code:
            referral_link = get_link_by_willt_code(referrer_code)
            if referral_link and referral_link.user:
                referrer = referral_link.user

        # Make a User
        user = get_or_create_user_by_email( email, referrer, self )
        user.update(first_name         = first_name,
                    last_name          = last_name,
                    address1           = address1,
                    address2           = address2,
                    city               = city,
                    province           = province,
                    country_code       = country_code,
                    postal_code        = postal_code,
                    latitude           = latitude,
                    longitude          = longitude,
                    phone              = phone,
                    email              = email,
                    shopify_id         = shopify_id,
                    ip                 = ip,
                    accepts_marketing  = accepts_marketing)

        # Make the ShopifyOrder
        o = create_shopify_order( app, token, order_id, order_num, 
                                  subtotal, referring_site, user )

        # Store the purchased items in the order
        o.items.extend( items )
        o.put()


class DoUninstalledApp( URIHandler ):
    def post( self ):
        Email.emailBarbara( "UNinstall %s" % self.request.query_string )

