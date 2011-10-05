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

from apps.link.models       import Link 
from apps.user.models       import User, get_or_create_user_by_email
from apps.order.models      import OrderShopify
from util                   import httplib2
from util.consts            import *
from util.model             import Model
from util.helpers           import generate_uuid

# ------------------------------------------------------------------------------
# Client Class Definition ------------------------------------------------------
# ------------------------------------------------------------------------------
class Client(Model, polymodel.PolyModel):
    """A Client or the website"""
    uuid          = db.StringProperty(indexed = True)
    email         = db.StringProperty(indexed=True)
    creation_time = db.DateTimeProperty(auto_now_add = True)
    passphrase    = db.StringProperty(indexed=True)

    def __init__(self, *args, **kwargs):
        self._memcache_key = kwargs['uuid'] if 'uuid' in kwargs else None 
        super(Client, self).__init__(*args, **kwargs)
    
    @staticmethod
    def _get_from_datastore(google_user):
        """Datastore retrieval using memcache_key"""
        return db.Query(Client).filter('uuid =', google_user).get()
        
    # ReferenceProperty
        # campaigns = list of Campaigns

def get_client_by_email( email ):
    return Client.all().filter( 'email =', email ).get()

def register(email, pass1, pass2):
    """ Attempt to create a new user. Returns [status, user, errMsg] -
        if status is 'ok' and user is a User model.
        Otherwise returns err-status for status, None for user and 
        errMsg is a user-facing error message"""

    status, client, errMsg = 'OK', None, ''
    clientAuth = Client.all().filter('email =', email).get()

    if clientAuth and clientAuth.passphrase != None: # username taken
        status, errMsg = 'EMAIL_TAKEN', 'That email address is already registered.'
    
    elif pass1 != pass2: # unmatching passwords
        status, errMsg = 'UNMATCHING_PASS', 'Those passwords don\'t match.'
    else:
        client = Client( key_name=email.lower(), uuid=generate_uuid(16),
                         email=email.lower(), passphrase=pass1 )
        client.put()

    return [status, client, errMsg]

def authenticate(email, passphrase):
    """ User authentication. Returns a list of [status, client, errMsg] - 
        if status is 'ok' then a Client model is the second element and,
        there is no error message.  Otherwise no client is returned
        and the third element is a user-facing error message
        Codes: OK               -> User
               EMAIL_NOT_FOUND  -> None
               INVALID_PASSWORD -> None 
    """

    # a query to try and authenticate this email address
    status, client, errMsg = '', None, ''
    clientAuth = Client.all().filter('email =', email).get()

    if clientAuth == None: # client not known
        status, errMsg = "EMAIL_NOT_FOUND", "That email was not found"
    
    elif clientAuth.passphrase != passphrase: # invalid password
        status, errMsg = 'INVALID_PASSWORD', 'Incorrect password'
    
    else:
        status, client = 'OK', clientAuth

    return [status, client, errMsg]


# ------------------------------------------------------------------------------
# ClientShopify Class Definition -----------------------------------------------
# ------------------------------------------------------------------------------
class ClientShopify( Client ):
    
    # User
    merchant = db.ReferenceProperty(db.Model, collection_name = "shopify_store")

    # Store properties
    name    = db.StringProperty( indexed = False )
    url     = db.LinkProperty  ( indexed = True )
    token   = db.StringProperty( default = '' )
    id      = db.StringProperty( indexed = True )

    # Store product img URLs and do something useful with them
    product_imgs  = db.StringListProperty( indexed = False )
    
    def __init__(self, *args, **kwargs):
        """ Initialize this obj """
        super(ClientShopify, self).__init__(*args, **kwargs)
    
    def validateSelf(self):
        """ Validate this obj's properties before storing in DB """
        # Fetch product imgs before saving in the DB
        pass

# Accessors --------------------------------------------------------------------
def get_shopify_client_by_url(store_url):
    store = ClientShopify.all().filter( 'url =', store_url ).get()
    return store

def get_or_create_shopify_store( store_url, store_token='', request_handler=None, app_type="" ):
    store = get_shopify_client_by_url(store_url)

    if store == None:
        store = create_shopify_store( store_url, store_token, request_handler, app_type )

    return store

# Constructor ------------------------------------------------------------------
def create_shopify_store( url, token, request_handler, app_type ):
    """ Create a Shopify Store as a Client"""

    # Query the Shopify API to learn more about this store
    data = get_store_info( url, token, app_type )

    # Make the Merchant
    merchant = get_or_create_user_by_email( email=data['email'], referrer=None, request_handler=request_handler )

    # Now, make the store
    uuid  = generate_uuid( 16 )
    store = ClientShopify( key_name = uuid,
                           uuid     = uuid,
                           email    = data['email'],
                           passphrase = '',
                           name     = data['name'],
                           url      = url,
                           token    = token,
                           id       = str(data['id']),
                           merchant = merchant  )

    # moved this here so we could pass the app_type
    store.product_imgs = get_product_imgs(url, token, app_type)
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
                     email      = data['email'], 
                     client     = store )
    return store

# Shopify API Calls  -----------------------------------------------------------
def get_store_info(store_url, store_token, app_type):

    url      = '%s/admin/shop.json' % ( store_url )
    if app_type == "referral":
        username = REFERRAL_SHOPIFY_API_KEY
        password = hashlib.md5(REFERRAL_SHOPIFY_API_SHARED_SECRET + store_token).hexdigest()
    elif app_type == 'buttons':
        username = BUTTONS_SHOPIFY_API_KEY
        password = hashlib.md5(BUTTONS_SHOPIFY_API_SHARED_SECRET + store_token).hexdigest()
    else:   
        username = SIBT_SHOPIFY_API_KEY
        password = hashlib.md5(SIBT_SHOPIFY_API_SHARED_SECRET + store_token).hexdigest()

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
    
    details = json.loads( result.read() ) 
    shop    = details['shop']
    logging.info('shop: %s' % (shop))
    
    return shop

def get_product_imgs(store_url, store_token, app_type):
    """ Fetch images for all the products in this store """

    url      = '%s/admin/products.json' % (store_url)
    
    # eventually this will be:
    # TODO: THIS V
    #SHOPIFY_APPS[app]['api_key']
    if app_type == "referral":
        username = REFERRAL_SHOPIFY_API_KEY
        password = hashlib.md5(REFERRAL_SHOPIFY_API_SHARED_SECRET + store_token).hexdigest()
    elif app_type == 'buttons':
        username = BUTTONS_SHOPIFY_API_KEY
        password = hashlib.md5(BUTTONS_SHOPIFY_API_SHARED_SECRET + store_token).hexdigest()
    else:   
        username = SIBT_SHOPIFY_API_KEY
        password = hashlib.md5(SIBT_SHOPIFY_API_SHARED_SECRET + store_token).hexdigest()

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
    details  = json.loads( result.read() ) #['orders'] # Fetch the order
    products = details['products']

    ret = []
    for p in products:
        for k, v in p.iteritems():
            if 'images' in k:
                if len(v) != 0:
                    img = v[0]['src'].split('?')[0]
                    ret.append( img )   
    return ret

