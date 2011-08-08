#!/usr/bin/env python
# Data models for our Users
# our Users are our client's clients
import logging

from datetime import datetime
from decimal  import *

from google.appengine.api import memcache
from google.appengine.api import urlfetch
from google.appengine.api import taskqueue
from google.appengine.ext import db
from models.model         import Model
from util.emails          import Email
from util.helpers         import *

import models.oauth

class EmailModel(Model):
    created = db.DateTimeProperty(auto_now_add=True)
    address = db.EmailProperty(indexed=True)
    user    = db.ReferenceProperty( db.Model, collection_name = 'emails' )
    
    def __init__(self, *args, **kwargs):
        self._memcache_key = kwargs['created'] if 'created' in kwargs else None 
        super(EmailModel, self).__init__(*args, **kwargs)
    
    @staticmethod
    def _get_from_datastore(created):
        """Datastore retrieval using memcache_key"""
        return db.Query(EmailModel).filter('created =', created).get()

def create_email_model( user, email ):
    if email != '':
        # Check to see if we have one already
        em = EmailModel.all().filter( 'address = ', email ).get()

        # If we don't have this email, make it!
        if em == None:
            em = EmailModel(key_name=email, address=email, user=user )
        
        # TODO: We might need to merge Users here
        if em.user.uuid != user.uuid:
            Email.emailBarbara( "CHECK OUT: %s %s. They might be the same person." % (em.user.uuid, user.uuid) )
            logging.error("CHECK OUT: %s %s. They might be the same person." % (em.user.uuid, user.uuid))
            em.user = user

        em.put()

class User( db.Expando ):
    # General Junk
    uuid            = db.StringProperty(indexed = True)
    creation_time   = db.DateTimeProperty(auto_now_add = True)
    #first_name      = db.StringProperty(indexed=False)
    #last_name       = db.StringProperty(indexed=False)
    #about_me_url    = db.LinkProperty( required = False, default = None )
    referrer        = db.ReferenceProperty(db.Model, collection_name='user-referrer') # will be User.uuid
    client          = db.ReferenceProperty(db.Model, collection_name='client_user')
    other_data      = db.StringListProperty()

    # Twitter Junk
    #twitter_handle  = db.StringProperty(indexed = True)
    #twitter_name    = db.StringProperty()
    #twitter_pic_url = db.LinkProperty( required = False, default = None )
    #twitter_followers_count = db.IntegerProperty(default = 0)
    twitter_access_token = db.ReferenceProperty(db.Model, collection_name='twitter-oauth')

    # Klout Junk
    #twitter_id          = db.StringProperty( indexed = False )
    #kscore              = db.FloatProperty( indexed = False, default = 1.0 )
    #slope               = db.FloatProperty( indexed = False )
    #network_score       = db.FloatProperty( indexed = False )
    #amplification_score = db.FloatProperty( indexed = False )
    #true_reach          = db.IntegerProperty( indexed = False )
    #topics              = db.ListProperty( str, indexed = False )

    # Facebook Junk
    #fb_identity = db.LinkProperty( required = False, indexed = True, default = None )

    # ReferenceProperty
    #emails = db.EmailProperty(indexed=True)
    
    def __init__(self, *args, **kwargs):
        self._memcache_key = kwargs['uuid'] if 'uuid' in kwargs else None 

        #if 'email' in kwargs and kwargs['email'] != '':
        #    create_email_model( self, kwargs['email'] )
       
        super(User, self).__init__(*args, **kwargs)

    def update( self, **kwargs ):
        for k in kwargs:
            if k == 'email':
                create_email_model( self, kwargs['email'] )
            elif k == 'twitter_access_token':
                self.twitter_access_token = kwargs['twitter_access_token']
            elif k == 'client':
                self.client = kwargs['client']
            elif k == 'referrer':
                self.referrer = kwargs['referrer']
            
            else:
                setattr( self, k, kwargs[k] )
        """
        if 'twitter_handle' in kwargs and kwargs['twitter_handle'] != '':
            self.twitter_handle = kwargs['twitter_handle']
        
        if 'twitter_name' in kwargs and kwargs['twitter_name'] != '':
            self.twitter_name = kwargs['twitter_name']
        
        if 'twitter_profile_pic' in kwargs and kwargs['twitter_profile_pic'] != '':
            self.twitter_profile_pic = kwargs['twitter_profile_pic']

        if 'twitter_follower_count' in kwargs and kwargs['twitter_follower_count'] != None:
            self.twitter_follower_count = kwargs['twitter_follower_count']

        if 'fb_identity' in kwargs and kwargs['fb_identity'] != '':
            self.fb_identity = kwargs['fb_identity']

        if 'first_name' in kwargs and kwargs['first_name'] != '':
            self.first_name = kwargs['first_name']
        
        if 'last_name' in kwargs and kwargs['last_name'] != '':
            self.last_name = kwargs['last_name']

        if 'email' in kwargs and kwargs['email'] != '':
            create_email_model( self, kwargs['email'] )

        if 'referrer' in kwargs and kwargs['referrer'] != None and self.referrer == None:
            self.referrer = kwargs['referrer']
        """
        self.put()

    def get_attr( self, attr_name ):
        if attr_name == 'email':
            return self.emails[0].address if self.emails.count() > 0 else ''

        if hasattr( self, attr_name ):
            return getattr( self, attr_name )

    def update_twitter_info(self, **kwargs):
        fields = ['twitter_handle', 'twitter_profile_pic', 'twitter_followers_count', 'twitter_name', 'twitter_access_token']
        insertion = {}
        for k in kwargs:
            if k in fields:
                insertion[k] = kwargs[k]
        self.update(**insertion)

# Gets by X
def get_user_by_uuid( uuid ):
    logging.info("Getting user by uuid " + str(uuid))
    user = User.all().filter('uuid =', uuid).get()
    return user

def get_user_by_twitter(t_handle):
    logging.info("Getting user by T: " + t_handle)
    user = User.all().filter('twitter_handle =', t_handle).get()
    if user != None:
        logging.info('Pulled user: %s %s %s %s' % (t_handle, user.get_attr('twitter_pic_url'), user.get_attr('twitter_name'), user.get_attr('twitter_followers_count')))
        
        # If we don't have Klout data, let's fetch it!
        if user.get_attr('kscore') == '1.0':
            # Query Klout API for data
            taskqueue.add( queue_name='socialAPI', 
                           url='/klout', 
                           name= 'klout%s%s' % (t_handle, generate_uuid( 10 )),
                           params={'twitter_handle' : t_handle} )
    return user

def get_user_by_facebook(fb_id):
    logging.info("Getting user by FB: " + fb_id)
    user = User.all().filter('fb_identity =', fb_id).get()
    return user

def get_user_by_email( email ):
    logging.info("Getting user by email: " + email)
    email_model = EmailModel.all().filter( 'address = ', email ).get()
    return email_model.user if email_model else None

# Create by X
def create_user_by_twitter(t_handle, referrer):
    """Create a new User object with the given attributes"""
    # check to see if this t_handle has an oauth token
    OAuthToken = models.oauth.get_oauth_by_twitter(t_handle)

    user = User(key_name=t_handle,
                uuid=generate_uuid(16),
                twitter_handle=t_handle,
                referrer=referrer)
    
    if OAuthToken:
        user.twitter_access_token=OAuthToken
    
    user.put()

    # Query the SocialGraphAPI
    taskqueue.add( queue_name='socialAPI', 
                   url='/socialGraphAPI', 
                   name= 'soc%s%s' % (t_handle, generate_uuid( 10 )),
                   params={'id' : 'http://www.twitter.com/%s' % t_handle, 'uuid' : user.uuid} )

    return user

def create_user_by_facebook(fb_id, first_name, last_name, email, referrer):
    """Create a new User object with the given attributes"""
    user = User(key_name=fb_id,
                uuid=generate_uuid(16), fb_identity=fb_id, 
                first_name=first_name, last_name=last_name,
                referrer=referrer)
    user.put()

    # Query the SocialGraphAPI
    taskqueue.add( queue_name='socialAPI', 
                   url='/socialGraphAPI', 
                   name= fb_id + generate_uuid( 10 ),
                   params={'id' : fb_id, 'uuid' : user.uuid} )

    return user

def create_user_by_email(email, referrer):
    """Create a new User object with the given attributes"""
    user = User(key_name=email, uuid=generate_uuid(16), 
                email=email, referrer=referrer)
    user.put()

    return user

# Get or Create by X
def get_or_create_user_by_twitter(t_handle, name='', followers=None, profile_pic='', referrer=None, request_handler=None):
    """Retrieve a user object if it is in the datastore, othereise create
      a new object"""

    # First try to find them by cookie
    user = get_user_by_cookie( request_handler )
    if user:
        # Update the info
        user.update( twitter_handle=t_handle, twitter_name=name, 
                     twitter_follower_count=followers, 
                     twitter_profile_pic=profile_pic, referrer=referrer)

    # Then, search by Twitter handle
    if user is None:
        user = get_user_by_twitter(t_handle)    
    
    # Otherwise, make a new one
    if user is None:
        logging.info("Creating user: " + t_handle)
        user = create_user_by_twitter(t_handle, referrer)

    # Set a cookie to identify the user in the future
    set_user_cookie( request_handler, user.uuid )

    logging.info('get_or_create_user: %s %s %s %s' % (t_handle, user.get_attr('twitter_pic_url'), user.get_attr('twitter_name'), user.get_attr('twitter_followers_count')))
    return user

def get_or_create_user_by_facebook(fb_id, first_name='', last_name='', email='', referrer=None, verified=None, gender='', request_handler=None):
    """Retrieve a user object if it is in the datastore, otherwise create
      a new object"""
     
    # First try to find them by cookie
    user = get_user_by_cookie( request_handler )
    if user:
        user.update( fb_identity=fb_id, first_name=first_name, 
                     last_name=last_name, email=email, referrer=referrer,
                     gender=gender, verifed=verified )

    # Try looking by FB identity
    if user is None:
        user = get_user_by_facebook(fb_id)
        if email != '':    
            create_email_model( self, email )
    
    # Otherwise, make a new one
    if user is None:
        logging.info("Creating user: " + fb_id)
        user = create_user_by_facebook(fb_id, first_name, last_name, email, referrer)
    
    # Set a cookie to identify the user in the future
    set_user_cookie( request_handler, user.uuid )
    
    return user

def get_or_create_user_by_email(email, referrer=None, request_handler=None):
    """Retrieve a user object if it is in the datastore, otherwise create
      a new object"""
    
    # First try to find them by cookie
    user = get_user_by_cookie( request_handler )
    if user:
        user.update( email=email, referrer=referrer )
    
    # Then find via email
    if user is None:
        user = get_user_by_email(email)  
    
    # Otherwise, make a new one
    if user is None:
        logging.info("Creating user: " + email)
        user = create_user_by_email(email, referrer)
    
    # Set a cookie to identify the user in the future
    set_user_cookie( request_handler, user.uuid )
    
    return user

def get_user_by_cookie(request_handler):
    uuid = read_user_cookie( request_handler )
    if uuid:
        return get_user_by_uuid( uuid )
    return None

