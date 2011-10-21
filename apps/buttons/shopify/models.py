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
from apps.client.shopify.models   import ShopifyClient
from apps.email.models    import Email
from apps.link.models     import Link
from apps.user.models     import get_or_create_user_by_cookie

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

    def __init__(self, *args, **kwargs):
        """ Initialize this model """
        super(ButtonsShopify, self).__init__(*args, **kwargs)

# Constructor ------------------------------------------------------------------
def create_shopify_buttons_app(client, app_token):

    uuid = generate_uuid( 16 )
    app = ButtonsShopify( key_name    = uuid,
                          uuid        = uuid,
                          client      = client,
                          store_name  = client.name, # Store name
                          store_url   = client.url, # Store url
                          store_id    = client.id, # Store id
                          store_token = app_token,
                          button_selector = "_willet_buttons_app" ) 
    app.put()
    
    # Define our script tag 
    tags = [{
        "script_tag": {
            "src": "%s/b/shopify/load/buttons.js?app_uuid=%s" % (
                URL,
                uuid
            ),
            "event": "onload"
        }
    }]

    # Install yourself in the Shopify store
    app.install_webhooks()
    app.install_script_tags(script_tags=tags)

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
def get_or_create_buttons_shopify_app(client, app_token):
    app = get_shopify_buttons_by_url( client.url )
    
    if app is None:
        app = create_shopify_buttons_app(client, app_token)
    
    return app

def get_shopify_buttons_by_url( url ):
    """ Fetch a Shopify obj from the DB via the store's url"""
    logging.info("Shopify: Looking for %s" % url)
    return ButtonsShopify.all().filter( 'store_url =', url ).get()
