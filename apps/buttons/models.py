#!/usr/bin/env python

# Buttons model
# Extends from "App"

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc"

#import hashlib, logging, datetime

#from django.utils         import simplejson as json
from google.appengine.ext import db

from apps.app.models      import App
#from apps.link.models     import Link
#from apps.user.models     import get_or_create_user_by_cookie

#from util.consts          import *
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
    """Clients install the buttons App"""    
    def __init__(self, *args, **kwargs):
        """ Initialize this model """
        super(Buttons, self).__init__(*args, **kwargs)

class ButtonsFBActions(Model):
    """We have various different FB actions (want, own)"""
    name = db.StringProperty()
    default_css = db.StringProperty()    
    
    def __init__(self, *args, **kwargs):
        """ Initialize this model """
        super(ButtonsFBActions, self).__init__(*args, **kwargs)
 
class ClientsButtons(Model):
    """Clients can add multiple buttons (want, own)""" 
    app_ = db.ReferenceProperty(Buttons, collection_name="buttons")
    action = db.ReferenceProperty(ButtonsFBActions, collection_name="_buttons")
    
    css_class = db.StringProperty()
    
    def __init__(self, *args, **kwargs):
        super(ClientsButtons, self).__init__(*args, **kwargs)

