#!/usr/bin/python

# client models
# data models for our clients and associated methods

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc"

import hashlib, logging, urllib, urllib2

from datetime               import datetime
from decimal                import *
from django.utils           import simplejson as json
from google.appengine.api   import memcache
from google.appengine.api   import urlfetch
from google.appengine.api   import taskqueue
from google.appengine.ext   import db
from google.appengine.ext.db import polymodel

from apps.client.models     import Client
from apps.link.models       import Link 
from apps.product.shopify.models import ProductShopify
from apps.user.models       import User
from apps.user.models       import get_or_create_user_by_email

from util                   import httplib2
from util.consts            import *
from util.helpers           import generate_uuid
from util.helpers           import url as build_url 
from util.shopify_helpers   import get_shopify_url
from util.memcache_ref_prop import MemcacheReferenceProperty

# ------------------------------------------------------------------------------
# ClientShopify Class Definition -----------------------------------------------
# ------------------------------------------------------------------------------
class ClientShopify( Client ):
    
    # User
    merchant = MemcacheReferenceProperty(db.Model, collection_name = "shopify_stores")

    # Store properties
    name    = db.StringProperty( indexed = False )
    url     = db.LinkProperty  ( indexed = True )
    domain  = db.LinkProperty  ( indexed = True )
    token   = db.StringProperty( default = '' )
    id      = db.StringProperty( indexed = True )

    # Store product img URLs and do something useful with them
    product_imgs  = db.StringListProperty( indexed = False )
    
    def __init__(self, *args, **kwargs):
        """ Initialize this obj """
        super(ClientShopify, self).__init__(*args, **kwargs)
    
    def validateSelf( self ):
        self.url = get_shopify_url( self.url )

    # Constructor
    @staticmethod
    def create( url_, token, request_handler, app_type ):
        """ Create a Shopify Store as a Client"""
        # TODO(Barbara): Technically, we can do all this on a queue.

        url_ = get_shopify_url( url_ )
        
        # Query the Shopify API to learn more about this store
        data = get_store_info( url_, token, app_type )
        
        # Make the Merchant 
        # Note: App is attached later to the UserCreation action
        merchant = get_or_create_user_by_email( data['email'], request_handler, None )
        logging.info( 'MERCHANT UUID %s' % merchant.uuid )
        logging.info( 'MERCHANT Key %s' % merchant.key() )

        # Now, make the store
        uuid  = generate_uuid( 16 )
        domain = get_shopify_url( data['domain'] )
        if domain == '':
            domain = url_

        store = ClientShopify( key_name = uuid,
                               uuid     = uuid,
                               email    = data['email'],
                               passphrase = '',
                               name     = data['name'],
                               url      = url_,
                               domain   = domain,
                               token    = token,
                               id       = str(data['id']),
                               merchant = merchant  )
        store.put()

        # Update the merchant with data from Shopify
        merchant.update( full_name  = data['shop_owner'], 
                         address1   = data['address1'],
                         address2   = data['address2'] if hasattr( data, 'address2') else '',
                         city       = data['city'],
                         province   = data['province'],
                         country    = data['country'],
                         postal_code= data['zip'],
                         phone      = data['phone'],
                         client     = store )
        
        logging.info({
            'client_uuid': uuid,
            'app_type'   : app_type
        })
        
        # Query the Shopify API to dl all Products
        taskqueue.add(
                url = build_url('FetchShopifyProducts'),
                params = {
                    'client_uuid': uuid,
                    'app_type'   : app_type
                }
            )

        return store

    # Accessors 
    @staticmethod
    def get_by_url(store_url):
        store_url = get_shopify_url( store_url )
        #logging.warning ("looking for client with url: %s" % store_url)
        store = ClientShopify.all().filter( 'url =', store_url ).get()
        return store

    @staticmethod
    def get_by_id( id ):
        return ClientShopify.all().filter( 'id =', id ).get()
    
    @staticmethod
    def get_by_uuid( uuid ):
        return ClientShopify.all().filter( 'uuid =', uuid ).get()

    @staticmethod
    def get_or_create( store_url, store_token='', request_handler=None, app_type="" ):
        store = ClientShopify.get_by_url(store_url)

        if not store:
            store = ClientShopify.create( store_url, 
                                          store_token, 
                                          request_handler,
                                          app_type )
        return store

    def get_products( self, app_type ):
        """ Fetch images for all the products in this store """

        # Construct the API URL
        url      = '%s/admin/products.json' % (self.url)
        
        # Fix inputs ( legacy )
        if app_type == "referral":
            app_type = 'ReferralShopify'
        elif app_type == "sibt": 
            app_type = 'SIBTShopify'
        elif app_type == 'buttons':
            app_type = "ButtonsShopify"
        
        # Grab Shopify API settings
        settings = SHOPIFY_APPS[app_type]

        username = settings['api_key'] 
        password = hashlib.md5(settings['api_secret'] + self.token).hexdigest()

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
        result = urllib2.urlopen(url)

        # Grab the data about the order from Shopify
        details  = json.loads( result.read() ) 
        products = details['products']

        for p in products:
            ProductShopify.create_from_json( self, p ) 

# Shopify API Calls  -----------------------------------------------------------
def get_store_info(store_url, store_token, app_type):
    
    # Fix inputs ( legacy )
    if app_type == "referral":
        app_type = 'ReferralShopify'
    elif app_type == "sibt": 
        app_type = 'SIBTShopify'
    elif app_type == "buttons": 
        app_type = 'ButtonsShopify'
    
    # Grab Shopify API settings
    settings = SHOPIFY_APPS[app_type]

    # Constuct the API URL
    url      = '%s/admin/shop.json' % ( store_url )
    username = settings['api_key'] 
    password = hashlib.md5(settings['api_secret'] + store_token).hexdigest()
    header   = {'content-type':'application/json'}
    h        = httplib2.Http()
    
    # Auth the http lib
    h.add_credentials(username, password)
    
    logging.info("Querying %s" % url )
    resp, content = h.request( url, "GET", headers = header)
    
    details = json.loads( content ) 
    logging.info( details )
    shop    = details['shop']
    logging.info('shop: %s' % (shop))
    
    return shop

def get_product_imgs(store_url, store_token, app_type):
    """ Fetch images for all the products in this store """
    # Fix inputs ( legacy )
    if app_type == "referral":
        app_type = 'ReferralShopify'
    elif app_type == "sibt": 
        app_type = 'SIBTShopify'
    
    # Grab Shopify API settings
    settings = SHOPIFY_APPS[app_type]
    
    # Construct the API URL
    url      = '%s/admin/products.json' % (store_url)
    username = settings['api_key'] 
    password = hashlib.md5(settings['api_secret'] + store_token).hexdigest()
    header   = {'content-type':'application/json'}
    h        = httplib2.Http()
    
    # Auth the http lib
    h.add_credentials(username, password)
    
    logging.info("Querying %s" % url )
    resp, content = h.request( url, "GET", headers = header)

    # Grab the data about the order from Shopify
    details  = json.loads( content ) #['orders'] # Fetch the order
    products = details['products']

    ret = []
    for p in products:
        for k, v in p.iteritems():
            if 'images' in k:
                if len(v) != 0:
                    img = v[0]['src'].split('?')[0]
                    ret.append( img )   
    return ret

