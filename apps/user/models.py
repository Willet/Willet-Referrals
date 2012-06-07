#!/usr/bin/env python

# Data models for our Users
# our Users are our client's clients

__author__ = "Willet, Inc."
__copyright__ = "Copyright 2011, Willet, Inc"

import logging

from django.utils import simplejson

from decimal import *
from time import time
from hmac import new as hmac
from hashlib import sha1
from traceback import print_tb

from google.appengine.api import memcache
from google.appengine.api import urlfetch
from google.appengine.api import taskqueue
from google.appengine.ext import deferred
from google.appengine.api import datastore_errors
from google.appengine.ext import db
from google.appengine.datastore import entity_pb

from apps.email.models import Email
from apps.user.actions import UserCreate

from util.consts import ADMIN_EMAILS
from util.consts import ADMIN_IPS
from util.consts import FACEBOOK_QUERY_URL
from util.consts import MEMCACHE_TIMEOUT
from util.consts import USING_DEV_SERVER
from util.helpers import *
from util.memcache_bucket_config import MemcacheBucketConfig
from util.memcache_bucket_config import batch_put
from util.memcache_ref_prop import MemcacheReferenceProperty
from util.model import Model

# ------------------------------------------------------------------------------
# EmailModel Class Definition --------------------------------------------------
# ------------------------------------------------------------------------------
class EmailModel(Model):
    created = db.DateTimeProperty(auto_now_add=True)
    address = db.EmailProperty(indexed=True)
    user = MemcacheReferenceProperty(db.Model, collection_name = 'emails')

    def __init__(self, *args, **kwargs):
        self._memcache_key = kwargs['created'] if 'created' in kwargs else generate_uuid(16)
        super(EmailModel, self).__init__(*args, **kwargs)

    def _validate_self(self):
        return True

    def __str__(self):
        return self.address

    @staticmethod
    def _get_from_datastore(created):
        """Datastore retrieval using memcache_key"""
        return db.Query(EmailModel).filter('created =', created).get()

    def _validate_self(self):
        return True

    # Constructor ------------------------------------------------------------------
    @classmethod
    def create(cls, user, email):
        if email != '' and email != None:
            # Check to see if we have one already
            em = cls.all().filter('address = ', email).get()

            # If we don't have this email, make it!
            if em == None:
                em = cls(key_name=email, address=email, user=user)

            else:
                try:
                    # Check if this is a returning user who has cleared their cookies
                    if em.user.uuid != user.uuid:
                        Email.emailDevTeam("CHECK OUT: %s(%s) %s. They might be the same person." % (em.address, em.user.uuid, user.uuid),
                                           subject='Duplicate user detected')

                        # TODO: We might need to merge Users here
                        em.user = user
                except Exception, e:
                    logging.error('%s.%s.create() error: %s' % (cls.__module__, cls.__name__, e), exc_info=True)

            em.put()

    # Retriever --------------------------------------------------------------------
    @classmethod
    def get_by_user(cls, user):
        return cls.all().filter('user =', user)
# end class


# TODO delete these deprecated functions after April 18, 2012 (1 month warning)
def create_email_model(user, email):
    raise DeprecationWarning('Replaced by EmailModel.create')
    EmailModel.create(user, email)

def get_emails_by_user(user):
    raise DeprecationWarning('Replaced by EmailModel.get_by_user')
    EmailModel.get_by_user(user)

# This method is not used anywhere, delete after April 18, 2012 (1 month warning)
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
            logging.error('Error getting action: %s' % e, exc_info=True)

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
class User(db.Expando):
    # General Junk
    uuid = db.StringProperty(indexed = True)
    creation_time = db.DateTimeProperty(auto_now_add = True)
    client = db.ReferenceProperty(db.Model, collection_name='client_user')
    memcache_bucket = db.StringProperty(indexed = False, default = "")
    twitter_access_token = db.ReferenceProperty(db.Model, collection_name='twitter-oauth')
    linkedin_access_token = db.ReferenceProperty(db.Model, collection_name='linkedin-users')
  # user -> User.get_full_name()

    # referrer is deprecated
    referrer = db.ReferenceProperty(db.Model, collection_name='user-referrer') # will be User.uuid

    # Memcache Bucket Config name
    _memcache_bucket_name = '_willet_user_put_bucket'

    def __init__(self, *args, **kwargs):
        self._memcache_key = kwargs['uuid'] if 'uuid' in kwargs else None
        super(User, self).__init__(*args, **kwargs)

    @staticmethod
    def _get_from_datastore(uuid):
        """Datastore retrieval using memcache_key"""
        logging.info("GETTING USER FROM DB")
        db_user = User.all().filter('uuid =', uuid).get()
        if not db_user:
            logging.warn("User does not exist in DB. Not authenticated...")
        return db_user

    def _validate_self(self):
        # TODO: add validation for properties that are absolutely expected
        return True

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

    def put_later(self):
        """Memcaches and defers the put"""

        key = self.get_key()

        mbc = MemcacheBucketConfig.get_or_create(self._memcache_bucket_name)
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
        # logging.debug('User::put(): Saving %s to memcache and datastore.' % key)
        timeout_ms = 100
        while True:
            logging.debug('User::put(): Trying %s.put, timeout_ms=%i.' % (self.__class__.__name__.lower(), timeout_ms))
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

    def hardPut(self):
        logging.debug("PUTTING %s" % self.__class__.__name__)
        try:
            self._validate_self()
        except NotImplementedError, e:
            logging.error(e)
        db.put(self)

    def get_key(self):
        return '%s-%s' % (self.__class__.__name__.lower(), self._memcache_key)

    def _validate_self(self):
        return True

    # Retrievers ------------------------------------------------------------------
    @classmethod
    def get(cls, memcache_key):
        """ Generic class retriever.  If possible, use this b/c it checks memcache
        for model before hitting database.

        Each subclass must have a staticmethod _get_from_datastore
        """

        # so now you can do Model.get(urihandler.request.get(id))) without
        # worrying about the resulting None.
        if memcache_key is None:
            return None  # None is definitely not a key, bro

        key = '%s-%s' % (cls.__name__.lower(), memcache_key)
        # logging.debug('User::get(): Pulling %s from memcache.' % key)
        data = memcache.get(key)
        if not data:
            logging.debug('User::get(): %s not found in memcache, hitting datastore.' % key)
            entity = cls._get_from_datastore(memcache_key)
            # Throw everything in the memcache when you pull it - it may never be saved
            if entity:
                memcache.set(key, db.model_to_protobuf(entity).Encode(), time=MEMCACHE_TIMEOUT)
            return entity
        else:
            logging.debug('User::get(): %s found in memcache!' % key)
            return db.model_from_protobuf(entity_pb.EntityProto(data))

    @classmethod
    def get_by_facebook(cls, fb_id):
        logging.info("Getting %s by FB: %s" % (cls.__name__, fb_id))
        user = cls.all().filter('fb_identity =', fb_id).get()
        return user

    @classmethod
    def get_by_facebook_for_taskqueue(cls, fb_id):
        """Returns a user that is safe for taskqueue writing"""
        logging.info("Getting %s by FB for taskqueue: %s" % (cls, fb_id))
        user = cls.all().filter('fb_identity =', fb_id).get()
        props = dict((k, v.__get(e, cls)) for k, v in cls.properties().iteritems())
        props.update(clone=True)
        newUser = cls(**props)
        newUser.save()
        return newUser

    @classmethod
    def get_by_email(cls, email):
        # TODO: Reduce exception handler to expected error
        if not email:
            return None

        logging.info("Getting %s by email: %s" % (cls, email))
        email_model = EmailModel.all().filter('address = ', email).get()
        try:
            return email_model.user
        except:
            return None

    @classmethod
    def get_by_cookie(cls, request_handler):
        """Read a user by cookie. Update IP address if present"""
        if request_handler:
            user_cookie = read_user_cookie(request_handler)
            if user_cookie:
                user = cls.get(user_cookie)
                if user:
                    ip = request_handler.request.remote_addr
                    user.add_ip(ip)
                    return user
        # If anything went wrong, return None
        return None

    # Constructors ---------------------------------------------------------------------
    @classmethod
    def create(cls, app):
        """Create a new User object with the given attributes"""
        uuid = generate_uuid(16)
        user = cls(key_name=uuid, uuid=uuid)
        user.put_later()

        UserCreate.create(user, app) # Store User creation action

        return user

    @classmethod
    def create_by_facebook(cls, fb_id, first_name, last_name, name, email, token, would_be, friends, app):
        """Create a new User object with the given attributes"""
        user = cls(key_name=fb_id,
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
        EmailModel.create(user, email)

        # Store User creation action
        UserCreate.create(user, app)

        # Query the SocialGraphAPI
        taskqueue.add(queue_name='socialAPI',
                       url='/socialGraphAPI',
                       name= fb_id + generate_uuid(10),
                       params={'id' : fb_id, 'uuid' : user.uuid})

        return user

    @classmethod
    def create_by_email(cls, email, app):
        """Create a new User object with the given attributes"""
        user = cls(key_name=email, uuid=generate_uuid(16))
        user.put() # cannot put_later() here; app creation relies on merchant

        EmailModel.create(user, email) # Store email

        if app:  # optional, really
            UserCreate.create(user, app) # Store User creation action

        return user

    # 'Retrieve or Construct'ers ------------------------------------------------------------
    @classmethod
    def get_or_create_by_facebook(fb_id, first_name='', last_name='', name='', email='',
                                  verified=None, gender='', token='', would_be=False, friends=[],
                                  request_handler=None, app=None):
        """Retrieve a user object if it is in the datastore, otherwise create
          a new object"""

        # First try to find them by cookie if request handle present
        user = cls.get_by_cookie(request_handler)

        # Try looking by FB identity
        if user is None:
            user = cls.get_by_facebook(fb_id)

        # Otherwise, make a new one
        if user is None:
            logging.info("Creating %s: %s" % (cls, fb_id))
            user = cls.create_by_facebook(fb_id, first_name, last_name, name,
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
            set_user_cookie(request_handler, user.uuid)

        return user

    @classmethod
    def get_or_create_by_email(cls, email, request_handler, app):
        """Retrieve a user object if it is in the datastore, otherwise create
          a new object"""

        # First try to find them by cookie
        user = cls.get_by_cookie(request_handler)

        # Then find via email
        if not user:
            user = cls.get_by_email(email)

        # Otherwise, make a new one
        if not user:
            logging.info("Creating %s: %s" % (cls, email))
            user = cls.create_by_email(email, app)

        # Set a cookie to identify the user in the future
        set_user_cookie(request_handler, user.uuid)

        return user

    @classmethod
    def get_or_create_by_cookie(cls, request_handler, app):
        user = cls.get_by_cookie(request_handler)
        if user is None:
            user = cls.create(app)
            ip = request_handler.request.remote_addr
            user.add_ip(ip)

        # Set a cookie to identify the user in the future
        set_user_cookie(request_handler, user.uuid)

        return user

    # Accessors -----------------------------------------------------------
    def has_ip(self, ip):
        user_ips = self.user_ips.get()
        if not user_ips:
            user_ips = UserIPs.get_or_create(self)

        if user_ips: # fix "argument of type 'NoneType' is not iterable" memlag
            return ip in user_ips.ips
        else:
            return []

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
            return None
        else:
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

    def get_pics(self):
        """ puts the users pics in a list"""
        pics = []
        if hasattr(self, 'facebook_profile_pic'):
            pics.append(getattr(self, 'facebook_profile_pic'))

        return pics

    def get_attr(self, attr_name):
        # get_attr? There has got to be a more pythonic way to do this!
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

        if hasattr(self, attr_name):
            return getattr(self, attr_name)
        else:
            return None

    def is_admin(self):
        # logging.info("Checking Admin status for %s (%s)" % (self.get_full_name(), self.uuid))
        if hasattr(self, 'user_is_admin'):
            logging.info("%s (%s) might be ADMIN (via cached check) %s" % (self.uuid, self.get_full_name(), self.user_is_admin))
            return self.user_is_admin
        is_admin = False

        emails = EmailModel.get_by_user(self)
        # Filter by user email
        for e in emails:
            if e.address in ADMIN_EMAILS:
                logging.info("%s (%s) is an ADMIN (via email check)" % (self.uuid, self.get_full_name()))
                is_admin = True
                break

        # Filter by IP
        if not is_admin:
            user_ips = self.user_ips.get()
            if user_ips:
                for i in user_ips.ips:
                    if i in ADMIN_IPS:
                        logging.info("%s (%s) is an ADMIN (via IP check)" % (self.uuid, self.get_full_name()))
                        is_admin = True
                        break

        self.user_is_admin = is_admin
        return is_admin

    # Mutators ----------------------------------------------------------------------
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

    def merge_data(self, u):
        """ Merge u into self. """
        if self.key() == u.key():
            return

        logging.info("merging %s into %s" % (u.uuid, self.uuid))

        props = u.dynamic_properties()
        for p in props:
            setattr(self, p, getattr(u, p))

        self.put_later()

    def update(self, **kwargs):
        for k in kwargs:
            if k == 'email':
                EmailModel.create(self, kwargs['email'])
            elif k == 'client':
                self.client = kwargs['client']
            elif k == 'referrer':
                self.referrer = kwargs['referrer']
            elif k == 'ip':
                if hasattr(self, 'ips') and kwargs['ip'] not in self.ips:
                    self.ips.append(kwargs['ip'])
                else:
                    self.ips = [ kwargs['ip'] ]

            elif kwargs[k] != '' and kwargs[k] != None and kwargs[k] != []:
                logging.info("Adding %s %s" % (k, kwargs[k]))
                setattr(self, k, kwargs[k])
        self.put_later()

    # Facebook helpers -------------------------------------------------------------
    def facebook_share(self, msg, img='', name='', desc='', link=None):
        """Share 'message' on behalf of this user. returns share_id, html_response
           example: fb_share_id, res = self.facebook_share(msg)...
                        ... self.response.out.write(res) """

        logging.info("LINK %s" % link)
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

                msg = msg.encode('ascii', 'ignore')
                if isinstance(msg, str):
                    logging.info("CONVERTING MSG")
                    msg = unicode(msg, 'utf-8', errors='ignore')


                try:
                    caption = link.app_.client.domain
                except:
                    caption = link.app_.client.url
                caption = caption.encode('ascii', 'ignore')
                if isinstance(caption, str):
                    logging.info("CONVERTING")
                    caption = unicode(caption, 'utf-8', errors='ignore')

                name = name.encode('ascii', 'ignore')
                if isinstance(name, str):
                    logging.info("CONVERTING name")
                    name = unicode(name, 'utf-8', errors='ignore')

                if desc == '':
                    desc = name
                desc = desc.encode('ascii', 'ignore')
                if isinstance(desc, str):
                    desc = unicode(desc, 'utf-8', errors='ignore')

                """
                logging.info("%s" % msg)
                logging.info("%s" % img)
                logging.info("%s" % link.get_willt_url())
                logging.info("%s" % desc)
                logging.info("%s" % name)
                logging.info("%s" % caption)
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
            logging.error('Error sending fb request: %s' % e)
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
        taskqueue.add(url = url('FetchFacebookData'),
                       params = { 'user_uuid' : self.uuid,
                                  'fb_id'     : self.fb_identity })

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

            msg = msg.encode('ascii', 'ignore')
            if isinstance(msg, str):
                logging.info("CONVERTING MSG")
                msg = unicode(msg, 'utf-8', errors='ignore')

            caption = store_domain.encode('ascii', 'ignore')
            if isinstance(caption, str):
                logging.info("CONVERTING")
                caption = unicode(caption, 'utf-8', errors='ignore')

            name = name.encode('ascii', 'ignore')
            if isinstance(name, str):
                logging.info("CONVERTING name")
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
        for i in range(0, len(ids)):
            id = ids[i]
            name = names[i]

            # Update the params - personalize the msg
            params.update({ 'message' : "Hey %s! %s" % (name.split(' ')[0], msg) })
            try:
                params = dict((key, value.encode('utf-8')) for key, value in params.iteritems())
            except:
                logging.warn('Cannot encode all UTF-8 characters for fb share')

            payload = urllib.urlencode(params)

            facebook_share_url = "https://graph.facebook.com/%s/feed" % id

            fb_response, plugin_response, fb_share_id = None, None, None
            try:
                #logging.info(facebook_share_url + params)
                fb_response = urlfetch.fetch(facebook_share_url,
                                              payload,
                                              method = urlfetch.POST,
                                              deadline = 7)
            except urlfetch.DownloadError, e:
                logging.error('Error sending fb request: %s' % e)
                return [], 'fail'
                # No response from facebook

            if fb_response is not None:
                fb_results = simplejson.loads(fb_response.content)

                if fb_results.has_key('id'):

                    fb_share_ids.append(fb_results['id'])

                    """
                    taskqueue.add(
                        url = url('FetchFriendFacebookData'),
                        params = { 'fb_id' : id }
                    )
                    """
                else:
                    fb_share_ids.append('fail')
                    logging.info(fb_results)

            else:
                # we are assuming a nil response means timeout and success
                pass

        return fb_share_ids

    def fb_post_multiple_products_to_friends (self, ids, names, msg, img, store_domain, link):

        # First, fetch the user's data.
        taskqueue.add(url = url('FetchFacebookData'),
                       params = { 'user_uuid' : self.uuid,
                                  'fb_id'     : self.fb_identity })

        # Then, first off messages to friends.
        try:
            """ We try to build the params, utf8 encode them"""
            params = {
                'access_token' : self.fb_access_token,
                'picture'      : img,
                'link'         : link.get_willt_url(),
                'caption'      : store_domain.encode('utf8')
            }

        except Exception, e:
            params = {
                'access_token' : self.fb_access_token,
                'picture'      : img,
                'link'         : link.get_willt_url(),
                'caption'      : ''
            }
            pass

        # For each person, share the message
        fb_share_ids = []
        for i in range(0, len(ids)):
            id = ids[i]
            name = names[i]

            # Update the params - personalize the msg
            params.update({ 'message' : "Hey %s! %s" % (name.split(' ')[0], msg) })
            payload = urllib.urlencode(params)

            facebook_share_url = "https://graph.facebook.com/%s/feed" % id

            fb_response, plugin_response, fb_share_id = None, None, None
            try:
                #logging.info(facebook_share_url + params)
                fb_response = urlfetch.fetch(facebook_share_url,
                                              payload,
                                              method = urlfetch.POST,
                                              deadline = 7)
            except urlfetch.DownloadError, e:
                logging.error('Error sending fb request: %s' % e)
                return [], 'fail'
                # No response from facebook

            if fb_response is not None:
                fb_results = simplejson.loads(fb_response.content)

                if fb_results.has_key('id'):

                    fb_share_ids.append(fb_results['id'])

                    """
                    taskqueue.add(
                        url = url('FetchFriendFacebookData'),
                        params = { 'fb_id' : id }
                    )
                    """
                else:
                    fb_share_ids.append('fail')
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
            logging.error('Error sending fb request: %s' % e)
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

        return fb_share_id, plugin_response
# end class


# TODO delete these deprecated functions after April 18, 2012 (1 month warning)
# DEPRECEATED - Gets by X
def get_user_by_facebook(fb_id):
    raise DeprecationWarning('Replaced by User.get_by_facebook')
    User.get_by_facebook(fb_id)

def get_user_by_facebook_for_taskqueue(fb_id):
    raise DeprecationWarning('Replaced by User.get_by_facebook_for_taskqueue')
    User.get_by_facebook_for_taskqueue(fb_id)

def get_user_by_email(email):
    raise DeprecationWarning('Replaced by User.get_by_email')
    User.get_by_email(email)

def get_user_by_cookie(request_handler):
    raise DeprecationWarning('Replaced by User.get_by_cookie')
    User.get_by_cookie(request_handler)

def create_user_by_facebook(*args, **kwargs):
    raise DeprecationWarning('Replaced by User.create_by_facebook')
    User.create_by_facebook(*args, **kwargs)

def create_user_by_email(email, app):
    raise DeprecationWarning('Replaced by User.create_by_email')
    User.create_by_email(email, app)

def create_user(app):
    raise DeprecationWarning('Replaced by User.create')
    User.create(app)

def get_or_create_user_by_facebook(*args, **kwargs):
    raise DeprecationWarning('Replaced by User.get_or_create_by_facebook')
    User.get_or_create_by_facebook(*args, **kwargs)

def get_or_create_user_by_email(email, request_handler, app):
    raise DeprecationWarning('Replaced by User.get_or_create_by_email')
    User.get_or_create_by_email(email, request_handler, app)

def get_or_create_user_by_cookie(request_handler, app):
    raise DeprecationWarning('Replaced by User.get_or_create_by_cookie')
    User.get_or_create_by_cookie(request_handler, app)


# -----
# UserIPs Class Definition
# -----
class UserIPs(Model):
    user = MemcacheReferenceProperty(User, collection_name="user_ips")
    ips = db.StringListProperty(default=None)
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
        return cls.all().filter('user =', user_uuid).get()
# end class
