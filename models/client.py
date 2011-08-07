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
from util.helpers         import generate_uuid

class Client(Model):
    """A WilletSocial Client"""
    uuid          = db.StringProperty(indexed = True)
    email         = db.StringProperty(indexed=True)
    creation_time = db.DateTimeProperty(auto_now_add = True)
    passphrase    = db.StringProperty(indexed=True)

    def __init__(self, *args, **kwargs):
        self._memcache_key = kwargs['uuid'] if 'uuid' in kwargs else None 
        super(Client, self).__init__(*args, **kwargs)
    
    @staticmethod
    def _get_from_datastore(google_user):
        """Datastore retrieval using memcache_key"""
        return db.Query(Client).filter('uuid =', google_user).get()
        
    # ReferenceProperty
        # campaigns = list of Campaigns

def get_client_by_email( email ):
    return Client.all().filter( 'email =', email ).get()

def register(email, pass1, pass2):
    """ Attempt to create a new user. Returns [status, user, errMsg] -
        if status is 'ok' and user is a User model.
        Otherwise returns err-status for status, None for user and 
        errMsg is a user-facing error message"""

    status, client, errMsg = 'OK', None, ''
    clientAuth = Client.all().filter('email =', email).get()

    if clientAuth and clientAuth.passphrase != None: # username taken
        status, errMsg = 'EMAIL_TAKEN', 'That email address is already registered.'
    
    elif pass1 != pass2: # unmatching passwords
        status, errMsg = 'UNMATCHING_PASS', 'Those passwords don\'t match.'
    else:
        client = Client( uuid=generate_uuid(16), email=email.lower(), passphrase=pass1 )
        client.put()

    return [status, client, errMsg]

def authenticate(email, passphrase):
    """ User authentication. Returns a list of [status, client, errMsg] - 
        if status is 'ok' then a Client model is the second element and,
        there is no error message.  Otherwise no client is returned
        and the third element is a user-facing error message
        Codes: OK               -> User
               EMAIL_NOT_FOUND  -> None
               INVALID_PASSWORD -> None 
    """

    # a query to try and authenticate this email address
    status, client, errMsg = '', None, ''
    clientAuth = Client.all().filter('email =', email).get()

    if clientAuth == None: # client not known
        status, errMsg = "EMAIL_NOT_FOUND", "That email was not found"
    
    elif clientAuth.passphrase != passphrase: # invalid password
        status, errMsg = 'INVALID_PASSWORD', 'Incorrect password'
    
    else:
        status, client = 'OK', clientAuth

    return [status, client, errMsg]
