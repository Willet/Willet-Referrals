#!/usr/bin/python

# An Order Model
# Stores information about a purchase / point of conversion
# Will be subclassed

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc"

import hashlib
import logging
from django.utils            import simplejson as json
from google.appengine.api    import urlfetch
from google.appengine.ext    import db

from apps.order.models       import Order
from apps.product.shopify.models import ProductShopify


from util                    import httplib2
from util.model              import Model
from util.helpers            import generate_uuid

# ------------------------------------------------------------------------------
# OrderShopify Class Definition ------------------------------------------------
# ------------------------------------------------------------------------------
class OrderShopify( Order ):
    """Model storing shopify_order data"""
    order_token    = db.StringProperty( indexed = True )
    order_id       = db.StringProperty( indexed = True )
    order_number   = db.StringProperty( indexed = False )
    
    store_name     = db.StringProperty( indexed = False )
    store_url      = db.StringProperty( indexed = False, required=False, default=None )
    
    referring_site = db.StringProperty( indexed = False, required=False, default=None ) # might be useful

    def __init__(self, *args, **kwargs):
        """ Initialize this object"""
        super(OrderShopify, self).__init__(*args, **kwargs)

# Constructor ------------------------------------------------------------------
def create_shopify_order( user, client, app, order_token, order_id ):
    """ Create an Order for a Shopify store """

    # Don't duplicate orders!
    o = get_shopify_order_by_id( order_id ) 
    if o != None:
        return o
    
    url      = '%s/admin/orders/95530442.json' % app.store_url
    username = app.settings['api_key'] 
    password = hashlib.md5(app.settings['api_secret'] + app.store_token).hexdigest()
    header   = {'content-type':'application/json'}
    h        = httplib2.Http()

    # Auth the http lib
    h.add_credentials(username, password)

    resp, content = h.request( url, "GET", headers = header)

    # Grab the data about the order from Shopify
    order = json.loads( content ) 

    items = []
    order_id = token = order_num = referring_site = subtotal = None
    first_name = last_name = address1 = address2 = city = None
    province = country_code = postal_code = latitude = longitude = None
    phone = email = shopify_id = ip = accepts_marketing = None

    # Parse the data
    for k, v in order['order'].iteritems():
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
 
    # Update the User
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

    # Make the Order
    uuid = generate_uuid( 16 )
    o = OrderShopify( key_name     = uuid,
                      uuid         = uuid,
                      order_token  = order_token,
                      order_id     = str(order_id),
                      client       = client,
                      store_name   = client.name,
                      store_url    = client.url,
                      order_number = str(order_num),
                      subtotal_price = float(subtotal), 
                      referring_site = referring_site,
                      products     = items,
                      user         = user )
    o.put()

    return o # return incase the caller wants it

# Accessors --------------------------------------------------------------------
def get_shopify_order_by_id( id ):
    return OrderShopify.all().filter( 'order_id =', str(id) ).get()

def get_shopify_order_by_token( t ):
    return OrderShopify.all().filter( 'order_token =', t ).get()
