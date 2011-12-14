#!/usr/bin/env/python

__author__    = "Willet, Inc."
__copyright__ = "Copyright 2011, Willet, Inc"

import datetime
import logging
from google.appengine.ext    import db

from apps.action.models import Action
from util.helpers       import generate_uuid

## -----------------------------------------------------------------------------
## UserCreate Subclass --------------------------------------------------------
## -----------------------------------------------------------------------------
class UserCreate( Action ):
    """ Stored when a new User is created. """
    
    def __str__(self):
        return 'UserCreate: %s(%s) %s' % (
                self.user.get_full_name(),
                self.user.uuid,
        )

    ## Constructor 
    @staticmethod
    def create( user, app ):
        # Make the action
        uuid = generate_uuid( 16 )
        act  = UserCreate( key_name = uuid,
                           uuid     = uuid,
                           user     = user,
                           app_     = app )
        act.put()
        logging.error("PUT USER CREATE ACTION")

    @staticmethod
    def get_by_user( user ):
        return UserCreate.all().filter( 'user =', user ).get()

class UserIsFBLoggedIn(Action):
    """ Stored when a new User is created. """
    
    def __str__(self):
        return 'UserCreate: %s(%s) %s' % (
                self.user.get_full_name(),
                self.user.uuid,
        )

    ## Constructor 
    @staticmethod
    def create(user, app=None, instance=None, url=None):
        # Make the action
        uuid = generate_uuid( 16 )
        act  = UserIsFBLoggedIn( key_name = uuid,
                           uuid     = uuid,
                           user     = user,
                           app_     = app )
        act.put()
        logging.error("PUT USER can haz facebooks")

    @staticmethod
    def get_by_user( user ):
        return UserIsFBLoggedIn.all().filter('user =', user).get()

