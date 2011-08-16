#!/usr/bin/python

__author__      = "Barbara Macdonald"
__copyright__   = "Copyright 2011, Barbara"

import base64, logging, urllib, urllib2

from django.utils import simplejson as json
from google.appengine.api import urlfetch
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app


from models.shopify import *
from util.consts    import *

def GetShopifyOrder( campaign_uuid, order_id ):
    campaign = get_campaign_by_uuid( campaign_uuid )

    url = '%s/admin/orders/#%s.json' % ( campaign.target_url, order_id )
    username = SHOPIFY_API_KEY
    password = SHOPIFY_API_PASSWORD

    # this creates a password manager
    passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
    # because we have put None at the start it will always
    # use this username/password combination for  urls
    # for which `theurl` is a super-url
    passman.add_password(None, theurl, username, password)

    # create the AuthHandler
    authhandler = urllib2.HTTPBasicAuthHandler(passman)

    opener = urllib2.build_opener(authhandler)

    # All calls to urllib2.urlopen will now use our handler
    # Make sure not to include the protocol in with the URL, or
    # HTTPPasswordMgrWithDefaultRealm will be very confused.
    # You must (of course) use it when fetching the page though.
    urllib2.install_opener(opener)

    # authentication is now handled automatically for us
    result = urllib2.urlopen(theurl)

    if result.status_code != 200:
        # Call failed ...
        # handle gracefully
        return # TODO(Barbara): fix this in the future

    # Grab the data about the order from Shopify
    order = json.loads( result.content )['order'] # Fetch the order

    items = []
    order_id = order_num = referring_site = subtotal = None
    bill_addr = None
    for k, v in order.iteritems():

        # Grab order details
        if k == 'id':
            order_id = v
        elif k == 'subtotal_price':
            subtotal = v
        elif k == 'order_number':
            order_num = v
        elif k == 'referring_site':
            referring_site = v
    
        # Grab the purchased items and save some information about them.
        elif 'line_items' in k:
            for j in v:
                i = ShopifyItem( name=j['name'], price=j['price'], product_id=j['product_id'])
                items.append( i )

        # Store User/ Customer data
        elif k == 'billing_address':
            if user:
                user.city      = v['city']
                user.province  = v['province']
                user.country_code = v['country_code']
                user.latitude  = v['latitude']
                user.longitude = v['longitude']
            else:
                bill_addr = v

        elif k == 'customer':
            if user is None:
                user = get_or_create_user_by_email( v['email'] )

            user.first_name = v['first_name']
            user.last_name  = v['last_name']
            user.shopify_customer_id = v['id']

            if bill_addr:
                user.city         = bill_addr['city']
                user.province     = bill_addr['province']
                user.country_code = bill_addr['country_code']
                user.latitude     = bill_addr['latitude']
                user.longitude    = bill_addr['longitude']
    
    # Save the new User data        
    user.put()

    # Make the ShopifyOrder
    o = create_shopify_order( campaign, order_id, order_num, subtotal, referring_site, user )

    # Store the purchased items in the order
    o.items.extend( items )



##-----------------------------------------------------------------------------##
##------------------------- The URI Router ------------------------------------##
##-----------------------------------------------------------------------------##
def main():
    application = webapp.WSGIApplication([ ('/shopifyPurchase', GetShopifyOrder) ], debug=USING_DEV_SERVER)
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
