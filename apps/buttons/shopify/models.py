#!/usr/bin/env python

# Buttons model
# Extends from "App"

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc"

import hashlib
import logging
import datetime

from django.utils         import simplejson as json
from google.appengine.ext import db

from apps.app.shopify.models import AppShopify
from apps.buttons.models  import Buttons, ClientsButtons, ButtonsFBActions 
from apps.client.models   import ClientShopify
from apps.email.models    import Email
from apps.link.models     import Link
from apps.user.models     import get_or_create_user_by_cookie

from util                 import httplib2
from util.consts          import *
from util.helpers         import generate_uuid

NUM_VOTE_SHARDS = 15

# basic layout:
#   client installs button app
#       client adds buttons
#       each button has a buttonFBAction type

# ------------------------------------------------------------------------------
# Button Class Definition --------------------------------------------------------
# ------------------------------------------------------------------------------
class ButtonsShopify(Buttons, AppShopify):

    #client = db.ReferenceProperty(ClientShopify, collection_name='shopify_buttons')
    title_selector = db.StringProperty()
    description_selector = db.StringProperty()
    image_selector = db.StringProperty()
    button_selector = db.StringProperty()

    def __init__(self, *args, **kwargs):
        """ Initialize this model """
        super(ButtonsShopify, self).__init__(*args, **kwargs)

# Constructor ------------------------------------------------------------------
def create_buttons_shopify_app(client, app_token):

    uuid = generate_uuid( 16 )
    app = ButtonsShopify(
        key_name    = uuid,
        uuid        = uuid,
        client      = client,
        store_name  = client.name, # Store name
        store_url   = client.url, # Store url
        store_id    = client.id, # Store id
        store_token = app_token
    )
    app.put()
    
    # Install yourself in the Shopify store
    self.install_webhooks()
    self.install_script_tags()

    # Email Barbara
    Email.emailBarbara(
        'ButtonsShopify Install: %s %s %s' % (
            uuid,
            client.name,
            client.url
        )
    )
    
    return app

# Accessors --------------------------------------------------------------------
def get_or_create_buttons_shopify_app( client ):
    app = get_buttons_shopify_app_by_store_id( client.id )
    if app is None:
        app = create_buttons_shopify_app( client )
    return app

def get_buttons_shopify_app_by_uuid(id):
    """ Fetch a Shopify obj from the DB via the uuid"""
    logging.info("Shopify: Looking for %s" % id)
    return ButtonsShopify.all().filter( 'uuid =', id ).get()

def get_buttons_shopify_app_by_store_id(id):
    """ Fetch a Shopify obj from the DB via the store's id"""
    logging.info("Shopify: Looking for %s" % id)
    return ButtonsShopify.all().filter( 'store_id =', id ).get()


