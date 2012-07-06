#!/usr/bin/env python

"""Data models for our Users our Users are our client's clients."""

__author__ = "Willet, Inc."
__copyright__ = "Copyright 2012, Willet, Inc"

import logging
import urllib

from django.utils import simplejson

from google.appengine.api import memcache
from google.appengine.api import urlfetch
from google.appengine.api import taskqueue
from google.appengine.ext import deferred
from google.appengine.ext import db
from google.appengine.datastore import entity_pb

from apps.email.models import Email

from util.consts import ADMIN_EMAILS, ADMIN_IPS, FACEBOOK_QUERY_URL, \
                        MEMCACHE_TIMEOUT
from util.helpers import common_items, generate_uuid, set_user_cookie, url
from util.memcache_bucket_config import MemcacheBucketConfig
from util.memcache_bucket_config import batch_put
from util.memcache_ref_prop import MemcacheReferenceProperty
from util.model import Model


class EmailModel(Model):
    """One-to-many email storage for the User class."""
    created = db.DateTimeProperty(auto_now_add=True)
    address = db.EmailProperty(indexed=True)
    user = MemcacheReferenceProperty(db.Model, collection_name='emails')

    def __init__(self, *args, **kwargs):
        if 'created' in kwargs:
            self._memcache_key = kwargs['created']
        else:
            self._memcache_key = generate_uuid(16)

        super(EmailModel, self).__init__(*args, **kwargs)

    def _validate_self(self):
        return True

    def __str__(self):
        return self.address

    @classmethod
    def _get_from_datastore(cls, created):
        """Datastore retrieval using memcache_key"""
        return db.Query(cls).filter('created =', created).get()

    @classmethod
    def get_or_create(cls, user, email):
        if not email:
            raise ValueError('Supply an email to create an EmailModel.')

        # Check to see if we have one already
        existing_model = cls.get_by_email(email)

        # get...
        if existing_model:
            try:
                # Check if this is a returning user who has cleared their cookies
                if existing_model.user.uuid != user.uuid:
                    '''
                    Email.emailDevTeam("CHECK OUT: %s(%s) %s. They might be the same person." % (
                                        existing_model.address,
                                        existing_model.user.uuid, user.uuid),
                                        subject='Duplicate user detected')
                    '''
                    logging.warn('merging two duplicate users.')
                    user.merge_data(existing_model.user)  # merge
                    existing_model.user = user  # replace reference
            except AttributeError, err:
                logging.error('wtf? user has no uuid.', exc_info=True)
        else:  # ... or create
            existing_model = cls(key_name=email, address=email, user=user)
        existing_model.put()

    @classmethod
    def get_by_email(cls, email):
        """Returns the first EmailModel with this address."""
        return cls.all().filter('address =', email).get()

    @classmethod
    def get_by_user(cls, user):
        return cls.all().filter('user =', user)


class User(db.Expando):
    """User class definition."""
    uuid = db.StringProperty(indexed=True)
    creation_time = db.DateTimeProperty(auto_now_add=True)

    # Presumably, the user object you can already get by doing
    # Client.get_by_user or User.get_by_client.
    client = db.ReferenceProperty(db.Model, collection_name='client_user')

    # ???
    memcache_bucket = db.StringProperty(indexed=False, default="")
    # user -> User.get_full_name()

    # Memcache Bucket Config name
    _memcache_bucket_name = '_willet_user_put_bucket'

    def __init__(self, *args, **kwargs):
        self._memcache_key = kwargs['uuid'] if 'uuid' in kwargs else None
        super(User, self).__init__(*args, **kwargs)

    @classmethod
    def _get_from_datastore(cls, uuid):
        """Datastore retrieval using memcache_key"""
        logging.info("GETTING USER FROM DB")
        db_user = cls.all().filter('uuid =', uuid).get()
        if not db_user:
            logging.warn("User does not exist in DB. Not authenticated...")
        return db_user

    def _validate_self(self):
        # TODO: add validation for properties that are absolutely expected
        return True

    def put(self):
        """Stores model instance in memcache and database"""
        logging.debug("PUTTING %s" % self.__class__.__name__)
        key = self.get_key()

        try:
            self._validate_self()
        except NotImplementedError, e:
            logging.error(e)
        db.put(self)

        logging.debug("user has been put().")

        # Memcache *after* model is given datastore key
        if self.key():
            logging.debug("user exists in DB, and is stored in memcache.")
            memcache.set(key, db.model_to_protobuf(self).Encode(),
                         time=MEMCACHE_TIMEOUT)
            memcache.set(str(self.key()), key, time=MEMCACHE_TIMEOUT)

        return True

    def put_later(self):
        """Memcaches and defers the put"""
        logging.warn("Putting later %s" % self.__class__.__name__)
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
        memcache.set(key, db.model_to_protobuf(self).Encode(),
                     time=MEMCACHE_TIMEOUT)
        memcache.set(str(self.key()), key, time=MEMCACHE_TIMEOUT)

        list_identities = memcache.get(bucket) or []

        # Don't add a User twice to the same bucket.
        if key not in list_identities:
            list_identities.append(key)

        logging.info('bucket length: %d/%d' % (len(list_identities), mbc.count))
        if len(list_identities) > mbc.count:
            memcache.set(bucket, [], time=MEMCACHE_TIMEOUT)
            logging.warn('bucket overflowing, persisting!')
            deferred.defer(batch_put, self._memcache_bucket_name, bucket,
                           list_identities, _queue='slow-deferred')
        else:
            memcache.set(bucket, list_identities, time=MEMCACHE_TIMEOUT)

        logging.info('put_later: %s' % self.uuid)

    def get_key(self):
        return '%s-%s' % (self.__class__.__name__.lower(), self._memcache_key)

    @classmethod
    def get(cls, memcache_key=None):
        """Class retriever.

        memcache_key must be a valid string. Function returns None if invalid:
        cls.get() => None
        cls.get(None) => None
        ...
        cls.get({invalid key}) => None
        """

        # so now you can do Model.get(urihandler.request.get(id))) without
        # worrying about the resulting None.
        if not memcache_key:
            return None  # None, 0, False, ... are definitely not keys, bro

        key = '%s-%s' % (cls.__name__.lower(), memcache_key)
        data = memcache.get(key)
        if not data:
            logging.debug('User::get(): %s not found in memcache, hitting datastore.' % key)
            entity = cls._get_from_datastore(memcache_key)
            # Throw everything in the memcache when you pull it - it may never be saved
            if entity:
                memcache.set(key, db.model_to_protobuf(entity).Encode(),
                             time=MEMCACHE_TIMEOUT)
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
    def get_by_email(cls, email=None):
        """Get a User by its email. Default: None"""
        logging.info("Getting %s by email: %s" % (cls, email))

        if not email:
            return None

        email_model = EmailModel.all().filter('address =', email).get() or None
        return getattr(email_model, 'user', None)

    @classmethod
    def get_by_cookie(cls, request_handler):
        """Read a user by cookie. Update IP address if present."""
        return request_handler.get_user()

    @classmethod
    def create(cls, app=None, **kwargs):
        """Create a new User object with the given attributes"""
        logging.info("CREATING USER")

        uuid = generate_uuid(16)
        kwargs['key_name'] = uuid
        kwargs['uuid'] = uuid

        user = cls(**kwargs)
        user.put()
        return user

    @classmethod
    def create_by_facebook(cls, fb_id, first_name, last_name, name, email,
                           token, would_be, friends, app):
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
        EmailModel.get_or_create(user, email)

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

        EmailModel.get_or_create(user, email) # Store email
        return user

    @classmethod
    def get_or_create_by_facebook(cls, fb_id, first_name='', last_name='',
                                  name='', email='', verified=None, gender='',
                                  token='', would_be=False, friends=[],
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
        user.update(fb_identity=fb_id,
                    fb_first_name=first_name,
                    fb_last_name=last_name,
                    fb_name=name,
                    email=email,
                    fb_gender=gender,
                    fb_verified=verified,
                    fb_access_token=token,
                    fb_friends=friends)

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
    def get_or_create_by_cookie(cls, request_handler, app=None):
        """I just made app optional."""
        user = cls.get_by_cookie(request_handler)
        if not user:
            user = cls.create(app)

        # Set a cookie to identify the user in the future
        set_user_cookie(request_handler, user.uuid)

        return user

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
            service supplied.

        hasattr() of a None is True.
        2012-06-11: take advantage of getattr(,,'') being falsy

        default: u''
        """
        if service == 'facebook':
            if getattr(self, 'fb_first_name', u''):
                return u'%s %s' % (getattr(self, 'fb_first_name', ''),
                                   getattr(self, 'fb_last_name', ''))
            if hasattr(self, 'fb_name'):
                return self.fb_name

        if getattr(self, 'full_name', u''):
            return getattr(self, 'full_name', u'')

        if getattr(self, 'first_name', ''):
            return u'%s %s' % (getattr(self, 'first_name', ''),
                               getattr(self, 'last_name', ''))

        if getattr(self, 'fb_first_name', ''):
            return u'%s %s' % (getattr(self, 'fb_first_name', ''),
                               getattr(self, 'fb_last_name', ''))

        if getattr(self, 'fb_name', u''):
            return getattr(self, 'fb_name', u'')

        # Twitter username
        if getattr(self, 't_handle', u''):
            logging.warn('passing user\'s twitter username as name!')
            return getattr(self, 't_handle', u'')

        if getattr(self, 'email', u''):
            logging.warn('passing user\'s email as name!')
            return getattr(self, 'email', u'')

        return u''

    name = property(get_full_name) # read-only property

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

    def get_attr(self, attr_name, default=None):
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
                return 'https://social-referral.appspot.com/static/imgs/happy_face.png'

        return getattr(self, attr_name, default)

    def is_admin(self, default=False, urihandler=None):
        """Returns True if current user is an admin.

        Checks used (in this order):
        - "user_is_admin" property in the user object
        - email, against a list of admin emails
        - ip, against a list of admin IPs; this is done only if a urihandler
          is supplied.
        """
        is_admin = default

        if hasattr(self, 'user_is_admin'):
            logging.info("%s (%s) might be ADMIN (via cached check) %s" % (
                          self.uuid, self.get_full_name(), self.user_is_admin))
            return self.user_is_admin

        emails = EmailModel.get_by_user(self)
        # intersection > 0 means user is an admin!
        if len(common_items(emails, ADMIN_EMAILS)) > 0:
            logging.info("%s (%s) is an ADMIN (via email check)" % (
                            self.uuid, self.get_full_name()))
            self.user_is_admin = True
            return True

        # Filter by IP
        if urihandler:
            user_ip = urihandler.request.remote_addr
            if user_ip in ADMIN_IPS:
                logging.info("%s (%s) is an ADMIN (via IP check)" % (
                                self.uuid, self.get_full_name()))
                self.user_is_admin = True
                return True

        self.user_is_admin = is_admin
        return is_admin

    def merge_data(self, u):
        """ Merge u into self."""
        if self.key() == u.key():
            return True

        logging.info("merging %s into %s" % (u.uuid, self.uuid))

        props = u.dynamic_properties()
        for p in props:
            setattr(self, p, getattr(u, p))

        self.put_later()

    def update(self, **kwargs):
        for k in kwargs:
            if k == 'email':
                EmailModel.get_or_create(self, kwargs['email'])
            elif k == 'client':
                self.client = kwargs['client']
            elif k == 'ip':
                if hasattr(self, 'ips') and kwargs['ip'] not in self.ips:
                    self.ips.append(kwargs['ip'])
                else:
                    self.ips = [kwargs['ip']]

            elif kwargs[k] != '' and kwargs[k] != None and kwargs[k] != []:
                logging.info("Adding %s %s" % (k, kwargs[k]))
                setattr(self, k, kwargs[k])
        self.put_later()

    def fb_post_to_friends(self, ids, names, msg, img, name, desc,
                           store_domain, link):
        """Post something on your selected facebook friends' wall."""

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
                'link'         : link.willet_url,
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
                'link'         : link.willet_url,
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
                else:
                    fb_share_ids.append('fail')
                    logging.info(fb_results)

            else:
                # we are assuming a nil response means timeout and success
                pass

        return fb_share_ids
