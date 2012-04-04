#!/usr/bin/env/python

__author__ = "Willet, Inc."
__copyright__ = "Copyright 2011, Willet, Inc"

import datetime
import logging

from google.appengine.ext import db
from apps.action.models import Action
from util.helpers import generate_uuid

## -----------------------------------------------------------------------------
## GaeBingoAlt Subclass --------------------------------------------------------
## -----------------------------------------------------------------------------
class GaeBingoAlt(Action):
    """ Stores the variation that a given User sees"""
    conversion_name = db.StringProperty(indexed = True)
    alt = db.StringProperty(indexed = False)

    def __str__(self):
        return 'GaeBingoAlt: %s(%s) %s: %s' % (self.user.get_full_name(), 
                                                self.user.uuid, 
                                                self.conversion_name,
                                                self.alt)

    ## Constructor 
    @staticmethod
    def create(user, app, conversion_name, alt):
        act = GaeBingoAlt.get_by_user_and_conversion(user, conversion_name)

        if act.count() == 0:
            uuid = generate_uuid(16)
            act = GaeBingoAlt(key_name = uuid,
                                uuid = uuid,
                                user = user,
                                app_ = app,
                                conversion_name = conversion_name,
                                alt = alt)
            act.put()

    ## Accessors  
    @staticmethod
    def get_by_user_and_conversion(u, c):
        return GaeBingoAlt.all().filter('user =',u).filter('conversion_name =',c)
