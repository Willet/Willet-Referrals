#!/usr/bin/python

# Referral model
# Extends from "App"

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc"

import hashlib, logging, datetime

from django.utils         import simplejson as json
from google.appengine.ext import db

from apps.app.models      import App
from util.consts          import *

# ------------------------------------------------------------------------------
# Referral Class Definition ----------------------------------------------------
# ------------------------------------------------------------------------------
class Referral( App ):
    """Model storing the data for a client's sharing app"""
    emailed_at_10 = db.BooleanProperty( default = False )
   
    product_name  = db.StringProperty( indexed = True )
    target_url    = db.LinkProperty  ( indexed = False )
    
    share_text    = db.StringProperty( indexed = False )
    webhook_url   = db.LinkProperty( indexed = False, default = None, required = False )

    def __init__(self, *args, **kwargs):
        """ Initialize this model """
        super(Referral, self).__init__(*args, **kwargs)
    
    def update( self, title, product_name, target_url, share_text, webhook_url ):
        """Update the app with new data"""
        self.title        = title
        self.product_name = product_name
        self.target_url   = target_url
        
        self.share_text   = share_text

        self.webhook_url  = webhook_url
        self.put()

# Accessors --------------------------------------------------------------------
def get_referral_app_by_url( url ):
    """ Fetch a Referral obj from the DB via the url """
    logging.info("Referral: Looking for %s" % url )
    return Referral.all().filter( 'target_url =', url ).get()
