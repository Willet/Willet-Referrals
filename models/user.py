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
from util.helpers         import *

class User(Model):
    # General Junk
    uuid            = db.StringProperty( indexed = True )
    first_name      = db.StringProperty(indexed=False)
    last_name       = db.StringProperty(indexed=False)
    email           = db.EmailProperty(indexed=True)
    creation_time   = db.DateTimeProperty(auto_now_add = True)
    about_me_url    = db.LinkProperty( required = False )
    referrer        = db.ReferenceProperty(db.Model, collection_name='user-referrer') # will be User.uuid

    # Twitter Junk
    twitter_handle  = db.StringProperty(indexed = True)
    twitter_name    = db.StringProperty()
    twitter_pic_url = db.LinkProperty( required = False )
    twitter_followers_count = db.IntegerProperty(default = 0)

    # Klout Junk
    twitter_id          = db.StringProperty( indexed = False )
    kscore              = db.FloatProperty( indexed = False, default = 1.0 )
    slope               = db.FloatProperty( indexed = False )
    network_score       = db.FloatProperty( indexed = False )
    amplification_score = db.FloatProperty( indexed = False )
    true_reach          = db.IntegerProperty( indexed = False )
    topics              = db.ListProperty( str, indexed = False )

    # Facebook Junk
    fb_identity = db.LinkProperty( required = False, indexed = True )
    
    def __init__(self, *args, **kwargs):
       self._memcache_key = kwargs['uuid'] if 'uuid' in kwargs else None 
       super(User, self).__init__(*args, **kwargs)

    @staticmethod
    def _get_from_datastore(twitter_handle):
       """Datastore retrieval using memcache_key"""
       return db.Query(User).filter('uuid =', twitter_handle).get()

# Gets by X
def get_user_by_uuid( uuid ):
    logging.info("Getting user by uuid " + uuid)
    user = User.all().filter('uuid =', uuid).get()
    if user != None:
        logging.info('Pulled user: %s %s %s %s' % (uuid, user.twitter_pic_url, user.twitter_name, user.twitter_followers_count))
    return user

def get_user_by_twitter(t_handle):
    logging.info("Getting user by T: " + t_handle)
    user = User.all().filter('twitter_handle =', t_handle).get()
    if user != None:
        logging.info('Pulled user: %s %s %s %s' % (t_handle, user.twitter_pic_url, user.twitter_name, user.twitter_followers_count))
        
        # If we don't have Klout data, let's fetch it!
        if user.kscore == 1.0:
            # Query Klout API for data
            taskqueue.add( queue_name='socialAPI', 
                           url='/klout', 
                           name= 'klout%s%s' % (t_handle + generate_uuid( 10 )),
                           params={'twitter_handle' : t_handle} )
    return user

def get_user_by_facebook(fb_id):
    logging.info("Getting user by FB: " + fb_id)
    user = User.all().filter('fb_identity =', fb_id).get()
    return user

def get_user_by_email( email ):
    logging.info("Getting user by email: " + email)
    user = User.all().filter('email =', email).get()
    return user

# Create by X
def create_user_by_twitter(t_handle, name, followers, profile_pic, referrer):
    """Create a new User object with the given attributes"""
    user = User(uuid=generate_uuid(16),
                twitter_handle=t_handle,
                twitter_name=name, 
                twitter_followers_count=followers, 
                twitter_pic_url=profile_pic, 
                referrer=referrer)
    user.put()

    # Query the SocialGraphAPI
    taskqueue.add( queue_name='socialAPI', 
                   url='/socialGraphAPI', 
                   name= 'soc%s%s' % (t_handle + generate_uuid( 10 )),
                   params={'id' : 'http://www.twitter.com/%s' % t_handle, 'uuid' : user.uuid} )

    return user

def create_user_by_facebook(fb_id, first_name, last_name, email, referrer):
    """Create a new User object with the given attributes"""
    user = User(uuid=generate_uuid(16), fb_identity=fb_id, 
                first_name=first_name, last_name=last_name, email=email, 
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
    user = User(uuid=generate_uuid(16), email=email, referrer=referrer)
    user.put()

    return user

# Get or Create by X
def get_or_create_user_by_twitter(t_handle, name='', followers='', profile_pic='', referrer=None):
    """Retrieve a user object if it is in the datastore, othereise create
      a new object"""
    user = get_user_by_twitter(t_handle)    
    if user is None:
        logging.info("Creating user: " + t_handle)
        user = create_user_by_twitter(t_handle, name, followers, profile_pic, referrer)
    logging.info('get_or_create_user: %s %s %s %s' % (t_handle, user.twitter_pic_url, user.twitter_name, user.twitter_followers_count))
    return user

def get_or_create_user_by_facebook(fb_id, first_name='', last_name='', email='', referrer=None):
    """Retrieve a user object if it is in the datastore, otherwise create
      a new object"""
    user = get_user_by_facebook(fb_id)
    if user is None:
        logging.info("Creating user: " + fb_id)
        user = create_user_by_facebook(fb_id, first_name, last_name, email, referrer)
    return user

def get_or_create_user_by_email(email, referrer=None):
    """Retrieve a user object if it is in the datastore, otherwise create
      a new object"""
    user = get_user_by_email(email)    
    if user is None:
        logging.info("Creating user: " + email)
        user = create_user_by_email(email, referrer)
    return user
