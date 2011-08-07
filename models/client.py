# client models
# data models for our clients and associated methods

__all__ = [
    'Client'
]
import logging

from datetime import datetime
from decimal  import *

from google.appengine.api import memcache
from google.appengine.api import urlfetch
from google.appengine.api import taskqueue
from google.appengine.ext import db

from models.model         import Model

class Client(Model):
    """A WilletSocial Client"""
    email         = db.StringProperty(indexed=True)
    creation_time = db.DateTimeProperty(auto_now_add = True)
    passphrase    = db.StringProperty(indexed=True)

    def __init__(self, *args, **kwargs):
        self._memcache_key = kwargs['google_user'] if 'google_user' in kwargs else None 
        super(Client, self).__init__(*args, **kwargs)
    
    @staticmethod
    def _get_from_datastore(google_user):
        """Datastore retrieval using memcache_key"""
        return db.Query(Client).filter('google_user =', google_user).get()
        
    # ReferenceProperty
        # campaigns = list of Campaigns

def get_client_by_email( email ):
    return Client.all().filter( 'email =', email ).get()

def register(email, pass1, pass2):
    """ Attempt to create a new user. Returns [status, user, errMsg] -
        if status is 'ok' and user is a User model.
        Otherwise returns err-code for status, None for user and 
        errMsg is a user-facing error message"""

    status, user, errMsg = 'OK', None, ''
    client = Client.all().filter('email =', email).get()

    if client and client.passphrase == None: # Someone logged in before the Google switch
        client.passphrase = pass1 # Store their pw
        client.put()

    elif client and client.passphrase != None: # username taken
        status, errMsg = 'EMAIL_TAKEN', 'That email address is already registered.'
    
    elif pass1 != pass2: # unmatching passwords
        status, errMsg = 'UNMATCHING_PASS', 'Those passwords don\'t match.'
    else:
        client = Client( email=email.lower(), passphrase=pass1 )
        client.put()

    return [status, client, errMsg]

def authenticate(email, passphrase):
    """ User authentication. Returns a list of [status, user, errMsg] - 
        if status is 'ok' then a user model is the second element and,
        there is no error message.  Otherwise no user is returned
        and the third element is a user-facing error message
        Codes: OK               -> User
               EMAIL_NOT_FOUND  -> None
               INVALID_PASSWORD -> None 
    """

    # a query to try and authenticate this email address
    code, user, userStr = '', None, ''
    userAuth = Client.all().filter('email =', email).get()

    if userAuth == None: # user not known
        code, userStr = "EMAIL_NOT_FOUND", "That email was not found"
    elif userAuth.passphrase != passphrase: # invalid password
        code, userStr = 'INVALID_PASSWORD', 'Incorrect password'
    else:
        code, user = 'OK', userAuth

    return [code, user, userStr]
