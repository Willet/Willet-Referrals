#!/usr/bin/env python

# Buttons model
# Extends from "App"

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc"

import hashlib, logging, datetime

from django.utils         import simplejson as json
from google.appengine.ext import db

from apps.app.models      import App
from apps.link.models     import Link
from apps.user.models     import get_or_create_user_by_cookie
from apps.button.models   import Buttons, ClientsButtons, ButtonFBActions 
from apps.client.models   import ShopifyClient

from util.consts          import *

NUM_VOTE_SHARDS = 15

# basic layout:
#   client installs button app
#       client adds buttons
#       each button has a buttonFBAction type

# ------------------------------------------------------------------------------
# Button Class Definition --------------------------------------------------------
# ------------------------------------------------------------------------------
class ButtonsShopify(Buttons):

    client = db.ReferenceProperty(ShopifyClient, collection_name='shopify_buttons')

    title_selector = db.StringProperty()
    description_selector = db.StringProperty()
    image_selector = db.StringProperty()
    button_selector = db.StringProperty()

    def __init__(self, *args, **kwargs):
        """ Initialize this model """
        super(ButtonsShopify, self).__init__(*args, **kwargs)

