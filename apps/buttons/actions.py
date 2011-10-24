#!/usr/bin/env/python

__author__    = "Willet, Inc."
__copyright__ = "Copyright 2011, Willet, Inc"

import datetime
import logging
from google.appengine.ext    import db

from apps.action.models import Action
from util.helpers       import generate_uuid

## -----------------------------------------------------------------------------
## WantAction Subclass --------------------------------------------------------
## -----------------------------------------------------------------------------
class WantAction( Action ):
    """ Stored if a User wants an item. """
    
    url = db.LinkProperty( indexed = True )

    # Link that caused the want action ...
    link = db.ReferenceProperty( db.Model, collection_name = "link_wants" )
    
    def __str__(self):
        return 'Want: %s(%s) %s' % (
                self.user.get_full_name(),
                self.user.uuid,
                self.app_.uuid
        )

    ## Constructor 
    @staticmethod
    def create( user, app, link ):
        # Make the action
        uuid = generate_uuid( 16 )
        act  = WantAction( key_name = uuid,
                           uuid     = uuid,
                           user     = user,
                           app_     = app,
                           link     = link,
                           url      = link.target_url )
        act.put()

    # Accessors
    @staticmethod
    def count():
        return WantAction.all().count()

    @staticmethod
    def get_all():
        return WantAction.all()
