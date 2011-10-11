#!/usr/bin/python

# A wrapper for the Shopify API

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc."

import hashlib, re

from django.utils       import simplejson as json

from apps.client.models import Client
from apps.order.models  import OrderShopify
from apps.user.models   import User, get_user_by_cookie

from util            import httplib2
from util.consts     import *
from util.helpers    import *
from util.urihandler import URIHandler
from util.gaesessions import get_current_session

##----------------------------------------------------------------------------##
## Specifics -----------------------------------------------------------------##
##----------------------------------------------------------------------------##
def add_referree_gift_to_shopify_order( order_id ):
    logging.info("Looking for order %s" % order_id )
    order = OrderShopify.all().filter( 'order_id = ', order_id ).get()
    if hasattr(order, 'user'):
        name = order.user.get_full_name()
    else:
        name = 'an unknown user'
    note  = 'GIFT - %s was referred by their friends to your store. Reward them by adding a gift to their order. Thanks, Willet!' % name 

    add_note_to_shopify_order( order, note )

def add_referrer_gift_to_shopify_order( order_id ):
    logging.info("Looking for order %s" % order_id )
    order = OrderShopify.all().filter( 'order_id = ', order_id ).get()
    if hasattr(order, 'user'):
        name = order.user.get_full_name()
    else:
        name = 'an unknown user'
    note  = 'GIFT - %s referred their friends to your store. Reward them for spreading their love for your store by adding a gift to their order.  Thanks, Willet!' % name 

    add_note_to_shopify_order( order, note )

##----------------------------------------------------------------------------##
## Generics ------------------------------------------------------------------##
##----------------------------------------------------------------------------##
def add_note_to_shopify_order( order, note ):
    if order != None:
        url      = '%s/admin/orders/%s.json' % ( order.store_url, order.order_id )
        
        #username = SHOPIFY_APPS['ReferralShopify']['api_key'] 
        #password = hashlib.md5(SHOPIFY_APPS['ReferralShopify']['api_secret'] + self.store_token).hexdigest()
        
        username = REFERRAL_SHOPIFY_API_KEY
        password = hashlib.md5(REFERRRAL_SHOPIFY_API_SHARED_SECRET + order.client.token).hexdigest()
        header   = {'content-type':'application/json'}
        h        = httplib2.Http()
        
        h.add_credentials( username, password )

        # First, GET the Order to see if there is a note already.
        resp, content = h.request( url, "GET" )
        details = json.loads( content )
        logging.info("GOT %r" % details)
        previous_note = details['order']['note']

        # Construct the new note message
        new_note = "%s \n %s" % (note, previous_note)

        # Second, PUT the new note to the Order
        data = { 'order' : { 'id' : int(order.order_id), 'note' : new_note } }
        payload = json.dumps( data )

        logging.info("PUTTING to %s %r " % ( url, payload) )
        resp, content = h.request( url, "PUT", body=payload, headers=header )
        
        logging.info('%r %r' % (resp, content))
    else:
        logging.info('tried to add note but order is None')
