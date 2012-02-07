#!/usr/bin/python

# Referral model
# Extends from "App"

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc"

import hashlib, logging, datetime


from django.utils         import simplejson as json
from google.appengine.api import taskqueue
from google.appengine.ext import db

from apps.app.models      import App
from apps.link.models     import Link
from util.consts          import *
from util.helpers         import set_clicked_cookie, set_referral_cookie, set_referrer_cookie
from util.memcache_ref_prop import MemcacheReferenceProperty
from util.model           import Model

# ------------------------------------------------------------------------------
# Referral Class Definition ----------------------------------------------------
# ------------------------------------------------------------------------------
class Referral( App ):
    """Model storing the data for a client's sharing app"""
    emailed_at_10 = db.BooleanProperty( default = False )
   
    product_name  = db.StringProperty( indexed = True )
    target_url    = db.LinkProperty  ( indexed = True )
    
    share_text    = db.StringProperty( indexed = False )
    webhook_url   = db.LinkProperty( indexed = False, default = None, required = False )

    def __init__(self, *args, **kwargs):
        """ Initialize this model """
        super(Referral, self).__init__(*args, **kwargs)
    
    def handleLinkClick( self, urihandler, link ):
        # TODO(Barbara): Pull this out for the action model

        code = link.willt_url_code

        # Fetch the clicked cookie for this willt code 
        clickCookie = urihandler.request.cookies.get(code, False)

        # If the User hasn't clicked on this before AND the User isn't a bot,
        if not clickCookie:
            
            # Set cookies
            logging.info('A %r' % (urihandler))
            logging.info('B %r' % (urihandler.response))
            logging.info('C %r' % (urihandler.response.headers))
            
            set_referrer_cookie(urihandler.response.headers, self.uuid, code)
            # set_clicked_cookie should be here but for some weird reason, that doesn't work.
            # Therefore, it's in Link::processes.py:: TrackWilltUrl
            
            # Add to clicks count
            link.increment_clicks()
            
        # Set the referral cookie in all cases
        set_referral_cookie(urihandler.response.headers, code)

        # Go to where the link points
        urihandler.redirect(link.target_url)

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


## -----------------------------------------------------------------------------
## -----------------------------------------------------------------------------
## -----------------------------------------------------------------------------
class Conversion(Model):
    """Model storing conversion data"""
    uuid     = db.StringProperty( indexed = True )
    created  = db.DateTimeProperty(auto_now_add=True)
    link     = db.ReferenceProperty( db.Model, collection_name="link_conversions" )
    referrer = MemcacheReferenceProperty( db.Model, collection_name="users_referrals" )
    referree = MemcacheReferenceProperty( db.Model, default = None, collection_name="users_been_referred" )
    referree_uid = db.StringProperty()
    app      = db.ReferenceProperty( db.Model, collection_name="app_conversions" )
    order    = db.StringProperty()

    def __init__(self, *args, **kwargs):
        self._memcache_key = kwargs['uuid'] if 'uuid' in kwargs else None 
        super(Conversion, self).__init__(*args, **kwargs)
    
    @staticmethod
    def _get_from_dataapp( uuid ):
        """Dataapp retrieval using memcache_key"""
        return db.Query(Conversion).filter('uuid =', uuid).get()

def create_conversion( link, app, referree_uid, referree, order_num ):
    uuid = generate_uuid(16)
    
    c = Conversion( key_name     = uuid,
                    uuid         = uuid,
                    link         = link,
                    referrer     = link.user,
                    referree     = referree,
                    referree_uid = referree_uid,
                    app          = app,
                    order        = order_num )
    c.put()

    return c # return incase the caller wants it
