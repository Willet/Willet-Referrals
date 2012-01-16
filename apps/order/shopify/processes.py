#!/usr/bin/env python

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc"

import hashlib
import logging

from django.utils                import simplejson as json
from google.appengine.api        import urlfetch

from apps.app.models             import App
from apps.client.models          import get_client_by_uuid
from apps.client.shopify.models  import ClientShopify
from apps.order.shopify.models   import OrderShopify
from apps.product.shopify.models import ProductShopify
from apps.user.models            import User
from apps.user.models            import get_user_by_cookie
from apps.user.models            import get_or_create_user_by_email
from apps.user.actions           import UserCreate

from util                        import httplib2
from util.helpers                import *
from util.urihandler             import URIHandler

class OrderIframeNotification(webapp.RequestHandler):
    """ When order.js is loaded on a confirmation page, it'll
        notify us here so that we can score a sale for this User"""
    
    def get( self ):
        client = get_client_by_uuid( self.request.get('client_uuid') )
        user   = User.get( self.request.get('user_uuid') )
        if user is None:
            user = get_user_by_cookie( self )

        # Grab order info from url
        url      = self.request.get( 'url' ).split( '/' )
        l        = len( url )
        token    = url[ l - 1 ]
        store_id = url[ l - 2 ]

        # Try to fetch order.
        # Have we been webhook-pinged by Shopify yet?
        # A bit of a race condition here ..
        order = OrderShopify.get_by_token( token )
        if order:
            logging.info("Have the order already")
            if order.user and order.user.key() != user.key():
                # Merge User data
                user.merge_data( order.user )
                
                # Delete the old User
                logging.info("Deleting %s" % order.user.uuid)
                UserCreate.get_by_user( order.user ).delete()

                order.user.delete()

            if order.user == None:
                logging.info("%s is new user for this order" % ( user.uuid ))
                order.user = user
                order.put()
        
        else:
            # Otherwise, make a new Shopify Order
            OrderShopify.create( user, client, token )

class OrderWebhookNotification(URIHandler):
    def get(self):
        return self.post()

    def post(self):
        # Try/catch around whole thing so we never return a 500 error to Shopify.
        try:
            logging.info("HEADERS : %s %r" % (
                self.request.headers,
                self.request.headers
                )
            )

            store_url = "http://%s" % self.request.headers['X-Shopify-Shop-Domain']
            logging.info("store: %s " % store_url)
            client = ClientShopify.get_by_url( store_url ) 

            # Grab the data about the order from Shopify
            order = json.loads(self.request.body) 

            items = []
            order_id = token = order_num = referring_site = subtotal = None
            first_name = last_name = address1 = address2 = city = None
            province = country_code = postal_code = latitude = longitude = None
            phone = email = shopify_id = ip = accepts_marketing = None

            for k, v in order.iteritems():
                logging.info("K: %s V: %s" % (k, v))
                
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
                        product = ProductShopify.get_by_shopify_id(str(j['product_id']))
                        if product:
                            items.append(product.key())

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
     
            # Fetch the order if we hve it.
            o = OrderShopify.get_by_token( token )
            if o == None:
                user = get_or_create_user_by_email( email, self, client.apps.get() )
            else:
                user = o.user
     
            # Update the User's info
            if user:
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
            else:
                logging.error('NO USER: %s' % token)

            if o == None:
                # Make the Order
                o = OrderShopify.create(
                    user,
                    client,
                    token,
                    order_id,
                    order_num, 
                    subtotal,
                    referring_site
                )
            else:
                # Otherise, update it.
                o.order_id = str(order_id)
                o.order_number = str(order_num)
                o.subtotal_price = float(subtotal)
                o.referring_site = referring_site

            # Store the purchased items in the order
            o.products.extend( items )
            o.put()
        except Exception, e:
            logging.error("Error occurred during Order processing: %s" % e)

