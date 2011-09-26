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

from util.consts          import *
from util.helpers         import generate_uuid
from util.model           import Model

NUM_VOTE_SHARDS = 15

# basic layout:
#   client installs button app
#       client adds buttons
#       each button has a buttonFBAction type

# ------------------------------------------------------------------------------
# Button Class Definition --------------------------------------------------------
# ------------------------------------------------------------------------------
class Buttons(App):
    
    def __init__(self, *args, **kwargs):
        """ Initialize this model """
        super(ButtonApp, self).__init__(*args, **kwargs)

class ClientsButtons(Model):
    
    app_ = db.ReferenceProperty(ButtonApp, collection_name="buttons")
    action = db.ReferenceProperty(ButtonFBAction, colleciton_name="_buttons")
    
    css_class = db.StringProperty()
    
    def __init__(self, *args, **kwargs):
        super(Button, self).__init__(*args, **kwargs)

class ButtonFBActions(Model):
    name = db.StringProperty()
    default_css = db.StringProperty()    
    
    def __init__(self, *args, **kwargs):
        """ Initialize this model """
        super(ButtonFBAction, self).__init__(*args, **kwargs)
    
