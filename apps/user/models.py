#!/usr/bin/env python

# Data models for our Users
# our Users are our client's clients

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc"

import logging
import sys
import inspect

from django.utils import simplejson

from calendar  import monthrange
from datetime  import datetime, timedelta, time as datetime_time
from decimal   import *
from time      import time
from hmac      import new as hmac
from hashlib   import sha1
from traceback import print_tb

from google.appengine.api import memcache
from google.appengine.api import urlfetch
from google.appengine.api import taskqueue
from google.appengine.ext import deferred
from google.appengine.api import datastore_errors
from google.appengine.ext import db
from google.appengine.datastore import entity_pb

from apps.email.models              import Email
from apps.user.actions              import UserCreate

from util.consts                    import ADMIN_EMAILS
from util.consts                    import ADMIN_IPS
from util.consts                    import FACEBOOK_QUERY_URL
from util.consts                    import MEMCACHE_TIMEOUT
from util.consts                    import USING_DEV_SERVER
from util.helpers                   import *
from util.memcache_bucket_config    import MemcacheBucketConfig
from util.memcache_bucket_config    import batch_put 
from util.memcache_ref_prop import MemcacheReferenceProperty
from util.model                     import Model

# ------------------------------------------------------------------------------
# EmailModel Class Definition --------------------------------------------------
# ------------------------------------------------------------------------------
class EmailModel(Model):
    created = db.DateTimeProperty(auto_now_add=True)
    address = db.EmailProperty(indexed=True)
    user    = MemcacheReferenceProperty( db.Model, collection_name = 'emails' )
    
    def __init__(self, *args, **kwargs):
        self._memcache_key = kwargs['created'] if 'created' in kwargs else generate_uuid(16)
        super(EmailModel, self).__init__(*args, **kwargs)
    
    @staticmethod
    def _get_from_datastore(created):
        """Datastore retrieval using memcache_key"""
        return db.Query(EmailModel).filter('created =', created).get()
    
# Constructor ------------------------------------------------------------------
def create_email_model( user, email ):
    if email != '' and email != None:
        # Check to see if we have one already
        em = EmailModel.all().filter( 'address = ', email ).get()
        
        # If we don't have this email, make it!
        if em == None:
            em = EmailModel(key_name=email, address=email, user=user )
        
        else:
            logging.error("FIRST: %s" % em.user.uuid )
            logging.error("SECOND %s" % user.uuid )

            try:
                if em.user.uuid != user.uuid:
                    Email.emailBarbara( "CHECK OUT: %s(%s) %s. They might be the same person." % (em.address, em.user.uuid, user.uuid) )
                    logging.error("CHECK OUT: %s %s. They might be the same person." % (em.user.uuid, user.uuid))
                    
                    # TODO: We might need to merge Users here
                    em.user = user
            except Exception, e:
                logging.error('create_email_model error: %s' % e, exc_info=True)
        
        em.put()
    
# Accessors --------------------------------------------------------------------
def get_emails_by_user( user ):
    return EmailModel.all().filter( 'user =', user )

#def deferred_user_put(user_uuid):
def deferred_user_put(bucket_key, list_keys, decrementing=False):
    logging.info("Batch putting a list of users to memcache: %s" % list_keys)
    mbc = MemcacheBucketConfig.get_or_create('_willet_user_put_bucket')
    users_to_put = []
    had_error = False
    user_dict = memcache.get_multi(list_keys)
    for key in list_keys:
        data = user_dict.get(key)
        try:
            user = db.model_from_protobuf(entity_pb.EntityProto(data))
        except AssertionError, e:
            old_key = mbc.get_bucket(mbc.count)
            if bucket_key != old_key and not decrementing and not had_error:
                # we dont want to do this for the last bucket because it will
                # duplicate the entries we are about to create
                old_count = mbc.count
                mbc.decrement_count()
                logging.warn(
                    'encounted error, going to decrement buckets from %s to %s' 
                    % (old_count, mbc.count), exc_info=True)

                last_keys = memcache.get(old_key) or []
                memcache.set(old_key, [], time=MEMCACHE_TIMEOUT)
                deferred.defer(deferred_user_put, old_key, last_keys, decrementing=True, _queue='slow-deferred')
                had_error = True
        except Exception, e:
            logging.error('error getting action: %s' % e, exc_info=True)

    try:
        def txn():
            db.put_async(users_to_put)
        db.run_in_transaction(txn)
        for user in users_to_put:
            if user.key():
                memcache_key = user.get_key()
                memcache.set(memcache_key, db.model_to_protobuf(user).Encode(), time=MEMCACHE_TIMEOUT)
    except Exception,e:
        logging.error('Error putting %s: %s' % (users_to_put, e), exc_info=True)

    if decrementing:
        logging.warn('decremented mbc `%s` to %d and removed %s' % (
            mbc.name, mbc.count, bucket_key))

# ------------------------------------------------------------------------------
# User Class Definition --------------------------------------------------------
# ------------------------------------------------------------------------------
class User( db.Expando ):
    # General Junk
    uuid                  = db.StringProperty(indexed = True)
    creation_time         = db.DateTimeProperty(auto_now_add = True)
    client                = db.ReferenceProperty(db.Model, collection_name='client_user')
    memcache_bucket       = db.StringProperty( indexed = False, default = "")
    twitter_access_token  = db.ReferenceProperty(db.Model, collection_name='twitter-oauth')
    linkedin_access_token = db.ReferenceProperty(db.Model, collection_name='linkedin-users')
    
    # referrer is deprecated
    referrer              = db.ReferenceProperty(db.Model, collection_name='user-referrer') # will be User.uuid
    
    # Memcache Bucket Config name
    _memcache_bucket_name = '_willet_user_put_bucket'
    
    def __init__(self, *args, **kwargs):
        self._memcache_key = kwargs['uuid'] if 'uuid' in kwargs else None 
        
        #if 'email' in kwargs and kwargs['email'] != '':
        #    create_email_model( self, kwargs['email'] )
       
        super(User, self).__init__(*args, **kwargs)
    
    # USER MEMCACHE METHODS
    @staticmethod
    def _get_from_datastore(uuid):
        """Datastore retrieval using memcache_key"""
        logging.info("GETTING USER FROM DB")
        db_user = User.all().filter('uuid =', uuid).get()
        if not db_user:
            logging.warn ("User does not exist in DB. Not authenticated...")
        return db_user

    def put_later(self):
        """Memcaches and defers the put"""
        
        if USING_DEV_SERVER:
            logging.debug("dev mode, putting user now...")
            self.put()
            return
        
        key = self.get_key()

        mbc    = MemcacheBucketConfig.get_or_create(self._memcache_bucket_name)
        bucket = self.memcache_bucket
        
        # If we haven't set the bucket OR
        # if the bucket we set doesn't exist anymore: GRAB A NEW BUCKET
        if bucket == "" or bucket > mbc.count:
            self.memcache_bucket = mbc.get_random_bucket()
            bucket = self.memcache_bucket
        logging.info('bucket: %s' % bucket)

        # Save to memcache AFTER setting memcache_bucket
        memcache.set(key, db.model_to_protobuf(self).Encode(), time=MEMCACHE_TIMEOUT)
        memcache.set(str(self.key()), key, time=MEMCACHE_TIMEOUT)
        
        list_identities = memcache.get(bucket) or []
        
        # Don't add a User twice to the same bucket.
        if key not in list_identities:
            list_identities.append(key)

        logging.info('bucket length: %d/%d' % (len(list_identities), mbc.count))
        if len(list_identities) > mbc.count:
            memcache.set(bucket, [], time=MEMCACHE_TIMEOUT)
            logging.warn('bucket overflowing, persisting!')
            deferred.defer(batch_put, self._memcache_bucket_name, bucket, list_identities, _queue='slow-deferred')
        else:
            memcache.set(bucket, list_identities, time=MEMCACHE_TIMEOUT)

        logging.info('put_later: %s' % self.uuid)
    
    def put(self):
        """Stores model instance in memcache and database"""
        key = self.get_key()
        logging.debug('Model::save(): Saving %s to memcache and datastore.' % key)
        timeout_ms = 100
        while True:
            logging.debug('Model::save(): Trying %s.put, timeout_ms=%i.' % (self.__class__.__name__.lower(), timeout_ms))
            try:
                self.hardPut() # Will validate the instance.
                logging.debug("user has been hardput().")
            except datastore_errors.Timeout:
                thread.sleep(timeout_ms)
                timeout_ms *= 2
            else:
                break
        # Memcache *after* model is given datastore key
        if self.key():
            logging.debug("user exists in DB, and is stored in memcache.")
            memcache.set(key, db.model_to_protobuf(self).Encode(), time=MEMCACHE_TIMEOUT)
            memcache.set(str(self.key()), key, time=MEMCACHE_TIMEOUT)
            
        return True

    def hardPut( self ):
        # By default, Python fcns return None
        # If you want to prevent an object from being saved to the db, have 
        # validateSelf return anyhting except None
        if self.validateSelf() == None:
            
            logging.debug("PUTTING %s" % self.__class__.__name__)
            db.put( self )
        
    def get_key(self):
        return '%s-%s' % (self.__class__.__name__.lower(), self._memcache_key)

    def validateSelf(self):
        pass

    @classmethod
    def get(cls, memcache_key):
        """Checks memcache for model before hitting database
        Each class must have a staticmethod get_from_datastore
        TODO(barbara): Enforce the above statement!!!
        Also, should it be: get_from_datastore OR _get_from_datastore?
        """
        key = '%s-%s' % (cls.__name__.lower(), memcache_key)
        logging.debug('Model::get(): Pulling %s from memcache.' % key)
        data = memcache.get(key)
        if not data:
            logging.debug('Model::get(): %s not found in memcache, hitting datastore.' % key)
            entity = cls._get_from_datastore(memcache_key)
            # Throw everything in the memcache when you pull it - it may never be saved
            if entity:
                memcache.set(key, db.model_to_protobuf(entity).Encode(), time=MEMCACHE_TIMEOUT)
            return entity
        else:
            logging.debug('Model::get(): %s found in memcache!' % key)
            return db.model_from_protobuf(entity_pb.EntityProto(data))

    def is_admin( self ):
        logging.info("Checking Admin status for %s (%s)" % (self.get_full_name(), self.uuid))
        if hasattr(self, 'user_is_admin'):
            logging.info("%s might be ADMIN (via cached check) %s" % (self.uuid, self.user_is_admin))
            return self.user_is_admin
        is_admin = False

        emails = get_emails_by_user( self )
        # Filter by user email
        for e in emails:
            if e.address in ADMIN_EMAILS:
                logging.info("%s is an ADMIN (via email check)" % (self.uuid))
                is_admin = True

        # Filter by IP
        if not is_admin:
            user_ips = self.user_ips.get()
            if user_ips:
                for i in user_ips.ips:
                    if i in ADMIN_IPS:
                        logging.info("%s is an ADMIN (via IP check)" % (self.uuid))
                        is_admin = True

        self.user_is_admin = is_admin
        return is_admin 

    def add_ip(self, ip):
        """gets the ips for this user and put_later's it to the datastore"""
        user_ips = self.user_ips.get()
        if not user_ips:
            user_ips = UserIPs.get_or_create(self)
        if not self.has_ip(ip):
            user_ips.add(ip)
            user_ips.put_later()
            return True
        return False

    def has_ip(self, ip):
        user_ips = self.user_ips.get()
        if not user_ips:
            user_ips = UserIPs.get_or_create(self)

        return ip in user_ips.ips

    def merge_data( self, u ):
        """ Merge u into self. """
        if self.key() == u.key():
            return

        logging.info("merging %s into %s" % ( u.uuid, self.uuid ))

        props = u.dynamic_properties()
        for p in props:
            setattr( self, p, getattr( u, p ) )

        self.put_later()

    def get_name_or_handle(self):
        name = self.get_handle()
        if name == None:
            name = self.get_full_name()
        return name

    def get_first_name(self):
        fname = None
        if hasattr(self, 'fb_first_name'):
            fname = self.fb_first_name
        elif hasattr(self, 'first_name'):
            fname = self.first_name
        elif hasattr(self, 'fb_name'):
            fname = self.fb_name
        elif hasattr(self, 'fb_username'):
            fname = self.fb_username
        else:
            fname = self.get_handle() 
        return fname

    def get_full_name(self, service=None):
        """attempts to get the users full name, with preference to the
            service supplied"""
        fname = None
        if hasattr(self, 'fb_first_name') and service == 'facebook':
            fname = '%s %s' % (
                self.fb_first_name,
                str(self.get_attr('fb_last_name'))
            )
        elif hasattr(self, 'fb_name') and service == 'facebook':
            fname = self.fb_name
        elif hasattr(self, 'full_name'):
            fname = self.full_name
        elif hasattr(self, 'first_name'):
            fname = self.first_name
        elif hasattr(self, 'fb_first_name'):
            fname = '%s %s' % (
                self.fb_first_name,
                str(self.get_attr('fb_last_name'))
            )
        elif hasattr(self, 'fb_name'):
            fname = self.fb_name
        elif hasattr(self, 't_handle'):
            fname = self.t_handle
        else:
            fname = self.get_attr('email')
        
        if fname == None or fname == '':
            fname = "User %s" % (self.uuid)

        return fname
    name = property(get_full_name)

    def get_handle(self, service=None):
        """returns the name of this user, depends on what service
            they registered with"""
        handle = None
        if hasattr(self, 'fb_name') and\
            (service == 'facebook' or service == None):
            handle = self.fb_name
        elif hasattr(self, 'fb_username') and\
            (service == 'facebook' or service == None):
                handle = self.fb_username
        else:
            handle = self.get_attr('email')

        if (handle == None or handle == '') and service != None:
            # if we didn't get a handle for that service, try again
            handle = self.get_handle()
        return handle

    def get_reach(self, service=None):
        """ returns this users social "reach" """
        reach = 0
        # ugly hacks for reach
        if service == 'f':
            service = 'facebook'

        if hasattr(self, 'fb_friends') and service == 'facebook':
            if type(self.fb_friends) == type(int()):
                reach += self.fb_friends
            else:
                reach += int(len(self.fb_friends))
        elif service == None or service == 'total':
            reach = self.get_reach('facebook')\
        
        return reach
    
    def update( self, **kwargs ):
        for k in kwargs:
            if k == 'email':
                create_email_model( self, kwargs['email'] )
            elif k == 'client':
                self.client = kwargs['client']
            elif k == 'referrer':
                self.referrer = kwargs['referrer']
            elif k == 'ip':
                if hasattr(self, 'ips') and kwargs['ip'] not in self.ips:
                    self.ips.append( kwargs['ip'])
                else: 
                    self.ips = [ kwargs['ip'] ]

            elif kwargs[k] != '' and kwargs[k] != None and kwargs[k] != []:
                #logging.info("Adding %s %s" % (k, kwargs[k]))
                setattr( self, k, kwargs[k] )
        self.put_later()
        
    def get_pics(self):
        """ puts the users pics in a list"""
        pics = [] 
        if hasattr(self, 'facebook_profile_pic'):
            pics.append(getattr(self, 'facebook_profile_pic'))
        
        return pics 

    def get_attr( self, attr_name ):
        if attr_name == 'email':
            try:
                return self.emails[0].address
            except Exception, e:
                #logging.debug('user has no email address')
                return ''
        
        if attr_name == 'pic':
            if hasattr(self, 'facebook_profile_pic'):
                return getattr(self, 'facebook_profile_pic')
            elif hasattr(self, 'fb_username'):
                return '%s%s/picture' % (
                        FACEBOOK_QUERY_URL,        
                        getattr(self, 'fb_identity')
                    ) 
            elif hasattr(self, 'fb_identity'):
                return '%s%s/picture' % (
                        FACEBOOK_QUERY_URL,        
                        getattr(self, 'fb_identity')
                    )
            else:
                return 'https://si0.twimg.com/sticky/default_profile_images/default_profile_3_normal.png'
        
        if hasattr( self, attr_name ):
            return getattr( self, attr_name )
        else:
            return None
    
    def facebook_share(self, msg, img='', name='', desc='', link=None):
        """Share 'message' on behalf of this user. returns share_id, html_response
           invoation: fb_share_id, res = self.facebook_share(msg)...
                        ... self.response.out.write(res) """
        
        logging.info("LINK %s" % link )
        facebook_share_url = "https://graph.facebook.com/%s/feed" % self.fb_identity
        if img != "":
            try:
                """ We try to build the params, utf8 encode them"""
                caption = link.app_.client.domain
                if not caption:
                    caption = ''
                params = {
                    'access_token': self.fb_access_token,
                    'message': msg.encode('utf8'),
                    'picture' : img,
                    'link' : link.get_willt_url(),
                    'description' : desc.encode('utf8'),
                    'name' : name.encode('utf8'),
                    'caption' : caption.encode('utf8')
                }
                #for param in params:
                #    params[param] = params[param].encode('utf8')
                #params = dict([(key, value.encode('utf8')) for key,value in params.iteritems()])
                params = urllib.urlencode(params)
            except Exception, e:
                logging.warn('there was an error encoding, do it the old way %s' % e, exc_info = True)

                msg = msg.encode( 'ascii', 'ignore' )
                if isinstance(msg, str):
                    logging.info("CONVERTING MSG")
                    msg = unicode(msg, 'utf-8', errors='ignore')


                try:
                    caption = link.app_.client.domain
                except:
                    caption = link.app_.client.url
                caption = caption.encode( 'ascii', 'ignore' )
                if isinstance(caption, str):
                    logging.info("CONVERTING")
                    caption = unicode(caption, 'utf-8', errors='ignore')
                
                name = name.encode( 'ascii', 'ignore' )
                if isinstance(name, str):
                    logging.info("CONVERTING name" )
                    name = unicode(name, 'utf-8', errors='ignore')
                
                if desc == '':
                    desc = name
                desc = desc.encode('ascii', 'ignore') 
                if isinstance(desc, str):
                    desc = unicode(desc, 'utf-8', errors='ignore')

                """
                logging.info("%s" % msg )
                logging.info("%s" % img )
                logging.info("%s" % link.get_willt_url() )
                logging.info("%s" % desc )
                logging.info("%s" % name )
                logging.info("%s" % caption )
                """

                params = urllib.urlencode({
                    'access_token': self.fb_access_token,
                    'message': msg,
                    'picture' : img,
                    'link' : link.get_willt_url(),
                    'description' : desc,
                    'name' : name,
                    'caption' : caption
                })
        else:
            if isinstance(msg, str):
                logging.info("CONVERTING MSG")
                msg = unicode(msg, 'utf-8', errors='ignore')

            params = urllib.urlencode({
                'access_token': self.fb_access_token,
                'message'     : msg   })

        fb_response, plugin_response, fb_share_id = None, None, None
        try:
            logging.info(facebook_share_url + params)
            fb_response = urlfetch.fetch(facebook_share_url, 
                                         params,
                                         method=urlfetch.POST,
                                         deadline=7)
        except urlfetch.DownloadError, e: 
            logging.error('error sending fb request: %s' % e)
            return None, 'fail'
            # No response from facebook
            
        if fb_response is not None:
            
            fb_results = simplejson.loads(fb_response.content)
            if fb_results.has_key('id'):
                fb_share_id, plugin_response = fb_results['id'], 'ok'
                taskqueue.add(
                    url = url('FetchFacebookData'),
                    params = {
                        'user_uuid': self.uuid,
                        'fb_id': self.fb_identity
                    }
                )
            else:
                fb_share_id, plugin_response = None, 'fail'
                logging.info(fb_results)
        else:
            # we are assuming a nil response means timeout and success
            fb_share_id, plugin_response = None, 'ok'
            
            
        return fb_share_id, plugin_response

    def fb_post_to_friends(self, ids, names, msg, img, name, desc, store_domain, link):

        # First, fetch the user's data.
        taskqueue.add( url    = url('FetchFacebookData'),
                       params = { 'user_uuid' : self.uuid, 
                                  'fb_id'     : self.fb_identity } )

        # Then, first off messages to friends.
        try:
            """ We try to build the params, utf8 encode them"""
            params = {
                'access_token' : self.fb_access_token,
                'picture'      : img,
                'link'         : link.get_willt_url(),
                'description'  : desc.encode('utf8'),
                'name'         : name.encode('utf8'),
                'caption'      : store_domain.encode('utf8')
            }

        except Exception, e:
            logging.warn('there was an error encoding, do it the old way %s' % e, exc_info = True)

            msg = msg.encode( 'ascii', 'ignore' )
            if isinstance(msg, str):
                logging.info("CONVERTING MSG")
                msg = unicode(msg, 'utf-8', errors='ignore')

            caption = store_domain.encode( 'ascii', 'ignore' )
            if isinstance(caption, str):
                logging.info("CONVERTING")
                caption = unicode(caption, 'utf-8', errors='ignore')
            
            name = name.encode( 'ascii', 'ignore' )
            if isinstance(name, str):
                logging.info("CONVERTING name" )
                name = unicode(name, 'utf-8', errors='ignore')
            
            desc = desc.encode('ascii', 'ignore') 
            if isinstance(desc, str):
                desc = unicode(desc, 'utf-8', errors='ignore')

            params = {
                'access_token' : self.fb_access_token,
                'picture'      : img,
                'link'         : link.get_willt_url(),
                'description'  : desc,
                'name'         : name,
                'caption'      : caption
            }

        # For each person, share the message
        fb_share_ids = []
        for i in range( 0, len( ids ) ):
            id   = ids[i]
            name = names[i]

            # Update the params - personalize the msg
            params.update( { 'message' : "Hey %s! %s" % (name.split(' ')[0], msg) } )
            payload = urllib.urlencode( params )

            facebook_share_url = "https://graph.facebook.com/%s/feed" % id

            fb_response, plugin_response, fb_share_id = None, None, None
            try:
                #logging.info(facebook_share_url + params)
                fb_response = urlfetch.fetch( facebook_share_url, 
                                              payload,
                                              method   = urlfetch.POST,
                                              deadline = 7 )
            except urlfetch.DownloadError, e: 
                logging.error('error sending fb request: %s' % e)
                return [], 'fail'
                # No response from facebook
                
            if fb_response is not None:
                fb_results = simplejson.loads(fb_response.content)
                
                if fb_results.has_key('id'):
                    
                    fb_share_ids.append( fb_results['id'] )
                    
                    """
                    taskqueue.add(
                        url    = url('FetchFriendFacebookData'),
                        params = { 'fb_id' : id }
                    )
                    """
                else:
                    fb_share_ids.append( 'fail' )
                    logging.info(fb_results)

            else:
                # we are assuming a nil response means timeout and success
                pass
            
        return fb_share_ids
    
    
    def facebook_action(self, action, obj, obj_link):
        """Does an ACTION on OBJECT on users timeline"""
        logging.info("FB Action %s %s %s" % (action, obj, obj_link))
            
        url = "https://graph.facebook.com/me/shopify_buttons:%s?" % action 
        params = urllib.urlencode({
            'access_token' : self.fb_access_token,
            obj            : obj_link
        })

        fb_response, plugin_response, fb_share_id = None, False, None
        try:
            logging.info(url + params)
            fb_response = urlfetch.fetch(
                url, 
                params,
                method=urlfetch.POST,
                deadline=7
            )
        except urlfetch.DownloadError, e: 
            logging.error('error sending fb request: %s' % e)
            plugin_response = False
        else:
            try:
                results_json = simplejson.loads(fb_response.content)
                fb_share_id = results_json['id']
                plugin_response = True
                    
                # let's pull this users info
                taskqueue.add(
                    url = '/fetchFB',
                    params = {
                        'fb_id': self.fb_identity
                    }
                )
            except Exception, e:
                fb_share_id = None
                plugin_response = False
                logging.error('Error posting action: %r' % fb_response)
                logging.error("%s %s" % (fb_response.status_code, fb_response.content))
            
        return fb_share_id, plugin_response 

# Gets by X
# TODO: move Gets, Creates, & Gets or Creates to static methods of User class, update dependencies
# Reason: any subclasses of User now get these methods too
def get_user_by_uuid( uuid ):
    logging.warn('THIS METHOD IS DEPRECATED: %s' % inspect.stack()[0][3])
    logging.info("Getting user by uuid " + str(uuid))
    #user = User.all().filter('uuid =', uuid).get()
    user = User.get(uuid)
    return user

def get_user_by_facebook(fb_id):
    logging.info("Getting user by FB: " + fb_id)
    user = User.all().filter('fb_identity =', fb_id).get()
    return user

def get_user_by_facebook_for_taskqueue(fb_id):
    """Returns a user that is safe for taskqueue writing"""
    logging.info("Getting user by FB for taskqueue: " + fb_id)
    user = User.all().filter('fb_identity =', fb_id).get()
    klass = user.__class__
    props = dict((k, v.__get(e, klass)) for k, v in klass.properties().iteritems())
    props.update(clone=True)
    newUser = klass(**props)
    newUser.save()
    return newUser

def get_user_by_email( email ):
    logging.info("Getting user by email: " + email)
    email_model = EmailModel.all().filter( 'address = ', email ).get()
    # fix throwing error on lagging memcache
    #return email_model.user if email_model else None
    try:
        return email_model.user
    except:
        return None


def create_user_by_facebook(fb_id, first_name, last_name, name, email, token, would_be, friends, app):
    """Create a new User object with the given attributes"""
    user = User(key_name=fb_id,
                uuid=generate_uuid(16),
                fb_identity=fb_id, 
                fb_first_name=first_name,
                fb_last_name=last_name,
                fb_name=name,
                fb_access_token=token,
                would_be=would_be)
    if friends:
        user.fb_friends = friends
    user.put_later()
    
    # Store email
    create_email_model( user, email )
    
    # Store User creation action
    UserCreate.create( user, app )
    
    # Query the SocialGraphAPI
    taskqueue.add( queue_name='socialAPI', 
                   url='/socialGraphAPI', 
                   name= fb_id + generate_uuid( 10 ),
                   params={'id' : fb_id, 'uuid' : user.uuid} )

    return user

def create_user_by_email( email, app ):
    """Create a new User object with the given attributes"""
    user = User( key_name = email, uuid = generate_uuid(16) )
    logging.info("Putting later: %s %s" % (user.uuid, user.key()))
    user.put_later()

    # Store email
    create_email_model( user, email )
    
    # Store User creation action
    UserCreate.create( user, app )
    
    return user

def create_user( app ):
    """Create a new User object with the given attributes"""
    uuid=generate_uuid(16)
    user = User( key_name = uuid, uuid = uuid )
    user.put_later()
    
    # Store User creation action
    UserCreate.create( user, app ) 
    
    return user

def get_or_create_user_by_facebook(
        fb_id, first_name='', last_name='', name='', email='',
        verified=None, gender='', token='', would_be=False, friends=[], 
        request_handler=None, app=None):
    """Retrieve a user object if it is in the datastore, otherwise create
      a new object"""
     
    # First try to find them by cookie if request handle present
    user = get_user_by_cookie(request_handler) 
    
    # Try looking by FB identity
    if user is None:
        user = get_user_by_facebook(fb_id)
    
    # Otherwise, make a new one
    if user is None:
        logging.info("Creating user: " + fb_id)
        user = create_user_by_facebook(fb_id, first_name, last_name, name, 
                                       email, token, would_be, friends, app)
        # check to see if this user was added by reading another user's social graph
        # if so, pull profile data
        if user.would_be:
            taskqueue.add(url = '/fetchFB', params = {'fb_id': user.fb_identity})
    
    # Update the user
    user.update(
        fb_identity=fb_id,
        fb_first_name=first_name, 
        fb_last_name=last_name,
        fb_name=name,
        email=email,
        referrer=referrer,
        fb_gender=gender,
        fb_verified=verified,
        fb_access_token=token,
        fb_friends=friends
    )

    # Set a cookie to identify the user in the future
    if request_handler is not None:
        set_user_cookie( request_handler, user.uuid )
    
    return user

def get_or_create_user_by_email( email, request_handler, app ):
    """Retrieve a user object if it is in the datastore, otherwise create
      a new object"""
    
    # First try to find them by cookie
    user = get_user_by_cookie( request_handler )
    
    # Then find via email
    if user is None:
        user = get_user_by_email( email )  
    
    # Otherwise, make a new one
    if user is None:
        logging.info("Creating user: " + email)
        user = create_user_by_email(email, app)
    
    # Set a cookie to identify the user in the future
    set_user_cookie( request_handler, user.uuid )
    
    return user

def add_ip_to_user(user_uuid, ip):
    """Done as a deferred task otherwise have to put a user everytime we get
    one by cookie"""
    logging.warn('this method is deprecated: add_ip_to_user')
    logging.info('adding %s to user %s' % (ip, user_uuid))
    def txn(user):
        if user:
            if hasattr(user, 'ips') and ip not in user.ips:
                user.ips.append(ip)
            else: 
                user.ips = [ip]
            user.save()
    user = User.get(user_uuid)
    db.run_in_transaction(txn, user)

def get_user_by_cookie(request_handler):
    """Read a user by cookie. Update IP address if present"""
    if request_handler == None:
        return None

    user = User.get(read_user_cookie(request_handler))
    if user:
        ip = request_handler.request.remote_addr
        user.add_ip(ip)
        #deferred.defer(add_ip_to_user, user.uuid, ip, _queue='slow-deferred')
    return user

def get_or_create_user_by_cookie( request_handler, app ): 
    user = get_user_by_cookie(request_handler)
    if user is None:
        user = create_user( app )
        ip = request_handler.request.remote_addr
        user.add_ip(ip)
        #deferred.defer(add_ip_to_user, user.uuid, ip, _queue='slow-deferred')

    # Set a cookie to identify the user in the future
    set_user_cookie(request_handler, user.uuid)

    return user

# -----
# UserIPs Class Definition
# -----
class UserIPs(Model):
    user = MemcacheReferenceProperty(User, collection_name="user_ips")
    ips  = db.StringListProperty(default=None)
    _memcache_bucket_name = '_willet_user_ips_bucket'

    def __init__(self, *args, **kwargs):
        if 'user_uuid' in kwargs:
            self._memcache_key = kwargs['user_uuid']
        else:
            self._memcache_key = None
        super(UserIPs, self).__init__(*args, **kwargs)

    def add(self, ip):
        if not ip in self.ips:
            self.ips.append(ip)
            return True
        return False

    def put_later(self):
        """Calls the mbc put later"""
        mbc = MemcacheBucketConfig.get_or_create(self._memcache_bucket_name)
        mbc.put_later(self)
        #MemcacheBucketConfig.put_later(self._memcache_bucket_name, self)

    @classmethod
    def get_or_create(cls, user):
        uips = cls.get(user.uuid)
        if not uips:
            uips = cls(user=user, user_uuid=user.uuid)

        return uips

    @classmethod
    def _get_from_datastore(cls, user_uuid):
        logging.info('getting by user_uuid: %s' % user_uuid)
        return cls.all().filter('user =', user_uuid).get()


# ------------------------------------------------------------------------------
# Relationship Class Definition ------------------------------------------------
# ------------------------------------------------------------------------------

# NOTE:
#
# This is a TENTATIVE model. It is not in use.
#
class Relationship(Model):
    """Model storing inter-user relationships data"""
    uuid      = db.StringProperty( indexed = True )
    created   = db.DateTimeProperty(auto_now_add=True)
    from_user = MemcacheReferenceProperty( db.Model, collection_name="from_relationships" )
    to_user   = MemcacheReferenceProperty( db.Model, default = None, collection_name="to_relationships" )
    type      = db.StringProperty( default = 'friend' )
    provider  = db.StringProperty( )

    def __init__(self, *args, **kwargs):
        self._memcache_key = kwargs['uuid'] if 'uuid' in kwargs else None 
        super(Relationship, self).__init__(*args, **kwargs)
    
    @staticmethod
    def _get_from_datastore( uuid ):
        """Datastore retrieval using memcache_key"""
        return db.Query(Relationship).filter('uuid =', uuid).get()

def create_relationship( from_u, to_u, provider = '' ):
    uuid = generate_uuid(16)
    
    r = Relationship( key_name  = uuid,
                      uuid      = uuid,
                      from_user = from_u,
                      to_user   = to_u,
                      provider  = provider )
    r.put()

    return r # return incase the caller wants it

