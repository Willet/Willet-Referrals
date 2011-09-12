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
    note  = '[Willet] %s was referred to your store by a friend. Please add a gift into their purchase as a reward for being referred. Thanks!' % order.user.get_full_name()

    add_note_to_shopify_order( order, note )

def add_referrer_gift_to_shopify_order( order_id ):
    logging.info("Looking for order %s" % order_id )
    order = OrderShopify.all().filter( 'order_id = ', order_id ).get()
    note  = '[Willet] %s referred their friends to your store. Please add a gift into their purchase as a reward for spreading their love for your store. Thanks!' % order.user.get_full_name()

    add_note_to_shopify_order( order, note )

##----------------------------------------------------------------------------##
## Generics ------------------------------------------------------------------##
##----------------------------------------------------------------------------##
def add_note_to_shopify_order( order, note ):
    url      = '%s/admin/orders/%s.json' % ( order.store_url, order.order_id )
    username = SHOPIFY_API_KEY
    password = hashlib.md5(SHOPIFY_API_SHARED_SECRET + order.client.store_token).hexdigest()
    header   = {'content-type':'application/json'}
    h        = httplib2.Http()
    
    h.add_credentials( username, password )

    data = { 'order' : { 'id' : int(order.order_id), 'note' : note } }
    payload = json.dumps( data )

    logging.info("PUTTING to %s %r " % ( url, payload) )
    resp, content = h.request( url, "PUT", body=payload, headers=header )
    
    logging.info('%r %r' % (resp, content))



    """
    url      = '%s/admin/orders/%s.json' % ( order.store_url, order.order_id )
    username = SHOPIFY_API_KEY
    password = hashlib.md5(SHOPIFY_API_SHARED_SECRET + order.campaign.store_token).hexdigest()

    # this creates a password manager
    passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
    # because we have put None at the start it will always
    # use this username/password combination for  urls
    # for which `url` is a super-url
    passman.add_password(None, url, username, password)

    # create the AuthHandler
    authhandler = urllib2.HTTPBasicAuthHandler(passman)

    opener = urllib2.build_opener(authhandler)

    # All calls to urllib2.urlopen will now use our handler
    # Make sure not to include the protocol in with the URL, or
    # HTTPPasswordMgrWithDefaultRealm will be very confused.
    # You must (of course) use it when fetching the page though.
    urllib2.install_opener(opener)
    
    # authentication is now handled automatically for us
    logging.info("Querying %s" % url )

    data = { 'id' : order.order_id, 'note' : note }
    payload = urllib.urlencode( data )

    result = urllib2.urlopen(url, payload)
    """
