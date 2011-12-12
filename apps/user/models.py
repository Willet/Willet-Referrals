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

import apps.oauth.models
from apps.email.models              import Email
from apps.user.actions              import UserCreate
from apps.user_analytics.models     import UserAnalytics
from apps.user_analytics.models     import UserAnalyticsServiceStats
from apps.user_analytics.models     import get_or_create_ss
from apps.user_analytics.models     import get_or_create_ua

from util                           import oauth2 as oauth
from util.consts                    import ADMIN_EMAILS
from util.consts                    import ADMIN_IPS
from util.consts                    import FACEBOOK_QUERY_URL
from util.consts                    import MEMCACHE_TIMEOUT
from util.helpers                   import *
from util.memcache_bucket_config    import MemcacheBucketConfig
from util.memcache_bucket_config    import batch_put 
from util.model                     import Model

# ------------------------------------------------------------------------------
# EmailModel Class Definition --------------------------------------------------
# ------------------------------------------------------------------------------
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
        return User.all().filter('uuid =', uuid).get()

    def put_later(self):
        """Memcaches and defers the put"""
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
            except datastore_errors.Timeout:
                thread.sleep(timeout_ms)
                timeout_ms *= 2
            else:
                break
        # Memcache *after* model is given datastore key
        if self.key():
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
            return self.user_is_admin
        is_admin = False

        emails = get_emails_by_user( self )
        # Filter by user email
        for e in emails:
            if e.address in ADMIN_EMAILS:
                logging.info("%s is an ADMIN (via email check)" % (self.uuid))
                is_admin = True

        # Filter by IP
        if not is_admin and hasattr(self, 'ips'):
            for i in self.ips:
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
        elif hasattr(self, 'linkedin_first_name'):
            fname = self.linkedin_first_name
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
        if hasattr(self, 't_handle') and service == 'twitter':
            fname = self.twitter_handle
        elif hasattr(self, 'linkedin_first_name') and service == 'linkedin':
            fname = '%s %s' % (
                self.linkedin_first_name, 
                str(self.get_attr('linkedin_last_name'))
            )
        elif hasattr(self, 'fb_first_name') and service == 'facebook':
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
        if hasattr(self, 'twitter_handle') and\
            (service == 'twitter' or service == None):
            handle = self.twitter_handle
        elif hasattr(self, 'linkedin_first_name') and\
            (service == 'linkedin' or service == None):
            handle = self.linkedin_first_name
        elif hasattr(self, 'fb_name') and\
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
        if service == 't':
            service = 'twitter'
        elif service == 'f':
            service = 'facebook'
        elif service == 'l':
            service = 'linkedin'

        if hasattr(self, 'titter_followers_count') and service == 'twitter':
            reach += int(self.twitter_followers_count)
        elif hasattr(self, 'linkedin_num_connections') and service == 'linkedin':
            reach += int(self.linkedin_num_connections)
        elif hasattr(self, 'fb_friends') and service == 'facebook':
            if type(self.fb_friends) == type(int()):
                reach += self.fb_friends
            else:
                reach += int(len(self.fb_friends))
        elif service == None or service == 'total':
            reach = self.get_reach('twitter')\
                    + self.get_reach('facebook')\
                    + self.get_reach('linkedin')
        return reach
    
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
            elif k == 'ip':
                if hasattr(self, 'ips') and kwargs['ip'] not in self.ips:
                    self.ips.append( kwargs['ip'])
                else: 
                    self.ips = [ kwargs['ip'] ]

            elif kwargs[k] != '' and kwargs[k] != None and kwargs[k] != []:
                #logging.info("Adding %s %s" % (k, kwargs[k]))
                setattr( self, k, kwargs[k] )
        self.put_later()
        """
        if 'twitter_handle' in kwargs an
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

    def get_pics(self):
        """ puts the users pics in a list"""
        pics = [] 
        if hasattr(self, 'facebook_profile_pic'):
            pics.append(getattr(self, 'facebook_profile_pic'))
        if hasattr(self, 'twitter_profile_pic'):
            pics.append(getattr(self, 'twitter_profile_pic'))
        if hasattr(self, 'linkedin_picture_url'):
            pics.append(getattr(self, 'linkedin_picture_url'))
        
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
            elif hasattr(self, 'twitter_profile_pic'):
                return getattr(self, 'twitter_profile_pic')
            elif hasattr(self, 'linkedin_picture_url'):
                return getattr(self, 'linkedin_picture_url')
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
    
    def update_twitter_info(self, **kwargs):
        fields = ['twitter_handle', 'twitter_profile_pic', 'twitter_followers_count', 'twitter_name', 'twitter_access_token']
        insertion = {}
        for k in kwargs:
            if k in fields:
                insertion[k] = kwargs[k]
        self.update(**insertion)
   
    def compute_analytics(self, scope='day', period_start=datetime.today()):
        """computes analytics for this user on this scope"""
        pass
        """
        midnight = datetime_time(0)
        period_start = period_start.combine(period_start.date(), midnight)
        if scope == 'day':
            # yesterday
            period_start -= timedelta(days=1)
            period_end = period_start + timedelta(days=1)
        elif scope == 'week':
            # this gets the day of the week, monday=0, sunday=6
            # we want the stats for a full week, so we make sure
            # we are on the first day of the week (monday, 0)
            start_dow = period_start.weekday()
            delta = timedelta(days=start_dow)
            
            period_start -= (delta + timedelta(days=7))

            # now we need the end of the period, 7 days later
            delta = timedelta(days = 7)
            period_end = period_start + delta
        else:
            # we are on the month scope
            # make sure we start on day 1 of the month
            # this is not zero indexed, so we are going to
            # subtract 1 from this value, so that if we are on
            # day 1, we don't timedelta subtract 1...
            # ... it makes sense if you think about it
            month = period_start.month
            year = period_start.year
            if month - 1 == 0:
                month = 12
                year -= 1
            
            period_start.replace(year=year, month=month, day=1)

            # monthrange returns a tuple of first weekday of the month
            # and the number of days in this month, so (int, int)
            # we take the second value to be the number of days to add
            # to the start of our period to get the entire month
            one_month = timedelta(
                days=monthrange(period_start.year, period_start.month)[1]
            )
                        
            # we want the first day of the next month
            period_end = period_start + one_month

        # okay we are going to calculate this users analytics
        # for this scope

        # 1. get all the links for this user in this scope
        if hasattr(self, 'user_'):
            links = self.user_.filter('creation_time >=', period_start)\
                        .filter('creation_time <', period_end)
        else:
            logging.info('user has no links, exciting')
            return # GTFO, user has no links
        
        # 2. okay, we are going to go through each link
        # and put them in a list for a particular campaign
        # then once we have a list of links for a")ampaign
        # we create an user_analytics from the links
        app_id = None
        app_links = []
        ua = None
        services = ['facebook', 'linkedin', 'twitter', 'email', 'total']
        for link in links:
            try:
                app = link.app_
            except Exception,e:
                logging.error('Error getting app for link: %s' % e, exc_info=True)
                continue

            if app.uuid != app_id:
                # new campaign, new useranalytics!
                ua = get_or_create_ua(
                    user = self,
                    app = app,
                    scope = scope,
                    period_start = period_start
                )
                
                stats = {}
                for service in services:
                    stats[service] = get_or_create_ss(ua, service)

                    # we get the reach for the service now too
                    # because we're awesome like that
                    stats[service].reach = self.get_reach(service)

                app_id = app.uuid

            # figure out which service we are using
            if link.tweet_id != '':
                service = 'twitter'
            elif link.facebook_share_id != '':
                service = 'facebook'
            elif link.linkedin_share_url != '':
                service = 'linkedin'
            elif link.email_sent == True:
                service = 'email'
            else:
                # couldn't find the service
                logging.error('error tracking user share that has no service')
                logging.error(link)
                continue # on to next link!
            
            # let's increment some counters! 
            # starting witht the shares!
            stats[service].shares += 1
            stats['total'].shares += 1
            
            # alright let's get some clicks
            clicks = link.count_clicks()
            stats[service].clicks += clicks 
            stats['total'].clicks += clicks

            # get the number of conversions...
            # step 4: ???
            # step 5: profit!
            conversions = 0
            profit = 0.0
            if hasattr(link, 'link_conversions'):
                for conversion in link.link_conversions:
                    try:
                        order_id = conversion.order
                        order = OrderShopify.all().filter('order_id =', order_id)
                        for o in order:
                            if hasattr(o, 'subtotal_price'):
                                profit += float(o.subtotal_price)
                    except:
                        # whatever
                        logging.error('exception getting conversions')
                    conversion += 1
            
            stats[service].profit += float(profit)
            stats['total'].profit += float(profit)

            stats[service].conversions += conversions
            stats['total'].conversions += conversions
            
            # let's save everything ...
            ua.put()
            stats[service].put()
            stats['total'].put()
        link_count = links.count()
        if link_count > 0:
            logging.warn('processed %d links' % link_count)
        else:
            logging.info('no links to process')   
        return
        """
    
    def get_analytics_for_app(self, 
            app=None, scope=None, order='period_start'):
        """ returns all the UA for this user for a 
            specified app """
        ret = None
        if app != None:
            #ret = self.users_analytics.filter('campaign=', campaign)
            ret = self.users_analytics
            logging.info ('user has %d UA' % ret.count())
            
            ret = ret.filter('app_ =', app)
            logging.info ('%d ua total' % ret.count())

            if not scope == None:
                ret = ret.filter('scope =', scope)
                logging.info ('%d ua total' % ret.count())

            if not order == None:
                ret = ret.order(order)
                logging.info ('%d ua total' % ret.count())
            #logging.info ('user has %d UA for campaign %s' % (ret.count(), campaign))
            
            #ret = UserAnalytics.all()#.filter('user =', self).filter('campaign =',campaign)
            #logging.info ('%d ua total' % ret.count())
            
            #ret = ret.filter('user =', self)
            #logging.info ('%d ua for user %s' % (ret.count(), self))

            #ret = ret.filter('campaign =', campaign)
            #logging.info ('%d ua for campaign %s' % (ret.count(), campaign))
        return ret
    
    def update_linkedin_info(self, extra={}):
        """updates the user attributes based on linkedin dict"""
        def linkedin_location(user, json):
            return json['country']['code']
        
        def linkedin_interests(user, json):
            l = []
            for interest in json.split(','):
                l.append(interest.strip())
            return l
        
        def linkedin_im_accounts(user, json):
            l = []
            if 'values' not in json:
                return l
            for value in json['values']:
                l.append(
                    '%s,%s' % (
                        value['im-account-type'],
                        value['im-account-name']
                    )
                )
            return l
        
        def linkedin_urls(user, json):
            l = []
            if 'values' not in json:
                return l
            for value in json['values']:
                l.append(value['url'])
            return l
        
        def linkedin_getlist(a_dict, key):
            l = []
            if 'values' not in a_dict:
                return l
            for value in a_dict['values']:
                if key in value:
                    l.append(value[key])
            return l
        
        def linkedin_connections(user, connections):
            l = []
            if 'values' not in connections:
                return l
            linkedin_connected_users = []
            for connection in connections['values']:
                l.append(connection['id'])
                new_user = get_or_create_user_by_linkedin(
                    connection['id'],
                    request_handler = None,
                    token = None,
                    referrer = None,
                    would_be = True,
                    extra = connection
                )
                linkedin_connected_users.append(new_user.key())
            user.update(
                linkedin_connected_users=linkedin_connected_users
            )
            return l
        
        mappings = {
            'headline': 'linkedin_headline',
            'firstName': 'linkedin_first_name',
            'lastName': 'linkedin_last_name',
            'numConnections': 'linkedin_num_connections',
            'numConnectionsCapped': 'linkedin_num_connections_capped',
            'location': {
                'attr': 'linkedin_location_country_code',
                'call': linkedin_location
            },
            'pictureUrl': 'linkedin_picture_url',
            'industry': 'linkedin_industry',
            'imAccounts': {
                'attr': 'linkedin_im_accounts',
                'call': linkedin_im_accounts
            },
            'interests': {
                'attr': 'linkedin_interests',
                'call': linkedin_interests
            },
            'memberUrlResources': {
                'attr': 'linkedin_urls',
                'key': 'url',
                'call': linkedin_getlist
            }, 
            'twitterAccounts': {
                'attr': 'linkedin_twitter_accounts',
                'key': 'providerAccountId',
                'call': linkedin_getlist
            },
            'connections': {
                'attr': 'linkedin_connections',
                'call': linkedin_connections
            }
        }
        for key in extra:
            try:
                if key not in mappings:
                    continue
                elif type(mappings[key]) == type(str()):
                    setattr(self, mappings[key], extra[key])
                else:
                    attr = mappings[key]['attr']
                    if 'key' in mappings[key]:
                        # use the defined key to call getlist
                        value = mappings[key]['call'](extra[key], mappings[key]['key'])
                    else:
                        value = mappings[key]['call'](self, extra[key])
                    if type(value) == type(list()):
                        if hasattr(self, attr):
                            old = self.get_attr(attr)
                            value.extend(old)
                    if value != []:
                        setattr(self, attr, value)
            except Exception, e:
                exception_type, exception, tb = sys.exc_info()
                logging.error('error updating user with linkedin dict:\n%s\n%s\n%s\n\n%s' % (e, print_tb(tb), key, extra[key]))
        self.put_later()
        return True
    #
    # Social Networking Share Functionality
    # 
    
    def tweet(self, message, img=None):
        """Tweet on behalf of a user. returns tweet_id, html_response.
           invocation: tweet_id, resp = user.tweet(message)
                       . . . self response.out.write(resp)"""
        
        # prepare the signed message to be sent to twitter
        if img != None:
            """
            twitter_post_url = 'http://upload.twitter.com/1/statuses/update_with_media.json'
            body= urllib.urlencode( {"status": message.encode("UTF-8"),
                                     "media[]" : img
                                                     } )
            
            content_type = "multipart/form-data"
            """
            message = "%s %s" % (message, img)
        else:
            twitter_post_url = 'http://api.twitter.com/1/statuses/update.json'
            body= urllib.urlencode( {"status": message.encode("UTF-8")} )
            content_type = "application/x-www-form-urlencoded"

        token = oauth.Token(
            key=self.twitter_access_token.oauth_token,
            secret=self.twitter_access_token.oauth_token_secret
        )

        consumer = oauth.Consumer(TWITTER_KEY, TWITTER_SECRET)

        client = oauth.Client(consumer, token)
        
        twitter_post_url = 'http://api.twitter.com/1/statuses/update.json'
        
        logging.info("Tweeting at %s" % twitter_post_url )
        
        response, content = client.request(
            twitter_post_url, 
            "POST", 
            body= urllib.urlencode( {"status": message.encode("UTF-8")} ),
            headers={ "Content-type":"application/x-www-form-urlencoded" }
        ) 
        logging.info("%r %r" % ( response, content ))

        res = simplejson.loads( content )

        # update user with info from twitter
        if res.has_key('id_str'):
            self.update_twitter_info(twitter_handle=res['user']['screen_name'],
                    twitter_profile_pic=res['user']['profile_image_url_https'],
                    twitter_name=res['user']['name'],
                    twitter_followers_count=res['user']['followers_count'])
            resp = "<script type='text/javascript'>" +\
                      "window.opener.shareComplete(); window.close();</script>"
            return res['id_str'], resp
        else:
            resp = "<script type='text/javascript'>" +\
                "window.opener.alert('Tweeting not successful');</script>"
            return None, resp
    
    def linkedin_share(self, message):
        """shares on linkedin on behalf of the user
            returns share_location, html_response
            invocation: share_location, resp = user.linkedin_share(message) ..."""
        
        linkedin_share_url = 'http://api.linkedin.com/v1/people/~/shares?twitter-post=true'
        body = '{"comment": "%s","visibility": {"code": "anyone"}}' % message
        params = {
            "oauth_consumer_key": LINKEDIN_KEY,
            "oauth_nonce": oauth.generate_nonce(),
            "oauth_timestamp": int(time()),
            "oauth_token" : self.linkedin_access_token.oauth_token,
            "oauth_version": "1.0"
        }
        token = oauth.Token(
            key=self.linkedin_access_token.oauth_token,
            secret=self.linkedin_access_token.oauth_token_secret
        )
        consumer = oauth.Consumer(LINKEDIN_KEY, LINKEDIN_SECRET)
        #req = oauth.Request(method="POST", url=url, body=body, headers={'x-li-format':'json'}, parameters=params)
        #signature_method = oauth.SignatureMethod_HMAC_SHA1()
        #req.sign_request(signature_method, consumer, token)
        
        client = oauth.Client(consumer, token)
        response, content = client.request(
            linkedin_share_url, 
            "POST", 
            body=body, 
            headers={
                'x-li-format':'json',
                'Content-Type': 'application/json'
            }
        )
        
        #params = {
        #    "oauth_consumer_key": LINKEDIN_KEY,
        #    "oauth_nonce": generate_uuid(16),
        #    "oauth_signature_method": "HMAC-SHA1",
        #    "oauth_timestamp": str(int(time())),
        #    "oauth_token" : self.linkedin_access_token.oauth_token,
        #    "oauth_version": "1.0"
        #}
        #params_encoded = '&'.join(['%s=%s' % (k, v) for k, v in params])
        #key = '&'.join([LINKEDIN_SECRET, self.linkedin_access_token.oauth_token])
        #msg = "&".join(["POST", linkedin_share_url, params_encoded])
        #signature = hmac(key, msg, sha1).digest().encode('base64').strip()
        #params['oauth_signature'] = signature
        #response = urlfetch.fetch(
        #    linkedin_share_url,
        #    payload=xml,
        #    method=urlfetch.POST,
        #    headers = params
        #)
        if int(response.status) == 201:
            # good response, get the location
            html_response = """<script type='text/javascript'>
                        window.opener.shareComplete(); window.close();
                    </script>"""
            content = response['location']
        else:
            # bad response, pop up an error
            logging.error('Error doing linkedin_share, response %s: %s\n\n%s\n\n%s\n%s\n%s' % (
                response.status,
                response,
                content,
                body,
                self.linkedin_access_token.oauth_token,
                self.linkedin_access_token.oauth_token_secret
            ))
            html_response = """
                <script type='text/javascript'>
                    window.opener.alert('LinkedIn sharing not successful');
                </script>
            """
            content = None
        logging.info('li share: %s' % response)
        return content, html_response
    
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
def get_user_by_uuid( uuid ):
    logging.warn('THIS METHOD IS DEPRECATED: %s' % inspect.stack()[0][3])
    logging.info("Getting user by uuid " + str(uuid))
    #user = User.all().filter('uuid =', uuid).get()
    user = User.get(uuid)
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

def get_user_by_linkedin(linkedin_id):
    logging.info("Getting user by LID: " + linkedin_id)
    user = User.all().filter('linkedin_id =', linkedin_id).get()
    if user != None:
        logging.info('Pulled user: %s' % linkedin_id)
    
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
    return email_model.user if email_model else None

# Create by X
def create_user_by_twitter(t_handle, referrer, ip=''):
    """Create a new User object with the given attributes"""
    raise Exception( "OLD code. Needs to be updated before usage.")

    # check to see if this t_handle has an oauth token
    OAuthToken = apps.oauth.models.get_oauth_by_twitter(t_handle)
    
    user = User(key_name=t_handle,
                uuid=generate_uuid(16),
                twitter_handle=t_handle,
                referrer=referrer,
                ip=ip)
    
    if OAuthToken:
        user.twitter_access_token=OAuthToken
    
    user.put()
    
    # Query the SocialGraphAPI
    taskqueue.add( queue_name='socialAPI', 
                   url='/socialGraphAPI', 
                   name= 'soc%s%s' % (t_handle, generate_uuid( 10 )),
                   params={'id' : 'http://www.twitter.com/%s' % t_handle, 'uuid' : user.uuid} )
    
    return user

def create_user_by_linkedin(linkedin_id, referrer, ip='', would_be=False):
    """Create a new User object with the given attributes"""
    raise Exception( "OLD code. Needs to be updated before usage.")
    
    # check to see if this t_handle has an oauth token
    OAuthToken = apps.oauth.models.get_oauth_by_linkedin(linkedin_id)
    
    user = User(
        key_name = linkedin_id,
        uuid = generate_uuid(16),
        linkedin_id = linkedin_id,
        referrer = referrer,
        ip = ip,
        would_be = would_be
    )
    
    if OAuthToken:
        user.linkedin_access_token=OAuthToken
    
    user.put()
    
    # Query the SocialGraphAPI
    taskqueue.add (
        queue_name='socialAPI', 
        url = '/socialGraphAPI', 
        name = 'soc%s%s' % (linkedin_id, generate_uuid(10)),
        params = {
            'id' : 'http://www.linkedin.com/profile/view?id=%s' % linkedin_id, 
            'uuid' : user.uuid
        }
    )
    
    return user

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

# Get or Create by X
def get_or_create_user_by_twitter(t_handle, name='', followers=None, profile_pic='', referrer=None, request_handler=None, token=None):
    """Retrieve a user object if it is in the datastore, othereise create
      a new object"""
    
    # First try to find them by cookie
    user = get_user_by_cookie( request_handler )
    
    # Then, search by Twitter handle
    if user is None:
        user = get_user_by_twitter(t_handle)    
    
    # Otherwise, make a new one
    if user is None:
        logging.info("Creating user: " + t_handle)
        user = create_user_by_twitter(t_handle, referrer)
    
    # Update the info
    user.update(twitter_handle=t_handle, twitter_name=name, 
                twitter_follower_count=followers, 
                twitter_profile_pic=profile_pic, referrer=referrer,
                twitter_access_token=token)

    # Set a cookie to identify the user in the future
    set_user_cookie(request_handler, user.uuid)
    
    logging.info('get_or_create_user: %s %s %s %s' % (t_handle, user.get_attr('twitter_pic_url'), user.get_attr('twitter_name'), user.get_attr('twitter_followers_count')))
    return user

def get_or_create_user_by_linkedin(linkedin_id, request_handler=None, token=None, referrer=None, would_be=False, extra={}):
    """Retrieve a user object if it is in the datastore, othereise create
      a new object"""
    
    # First try to find them by cookie
    if request_handler != None:
        user = get_user_by_cookie(request_handler)
    else:
        user = None
       
    # Then, search by linkedin handle
    if user is None:
        user = get_user_by_linkedin(linkedin_id)
    
    # Otherwise, make a new one
    if user is None:
        logging.info("Creating user with linkedin_id: %s" % linkedin_id)
        user = create_user_by_linkedin(linkedin_id, referrer, would_be=would_be)
    
    # Update the info
    user.update(linkedin_id=linkedin_id, referrer=referrer, linkedin_access_token=token)

    # set the linkedin extra fields
    user.update_linkedin_info(extra)
    
    # Set a cookie to identify the user in the future
    if request_handler != None:
        set_user_cookie(request_handler, user.uuid)
     
    logging.info('get_or_create_user: %s' % linkedin_id)
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
    user = db.ReferenceProperty(User, collection_name="user_ips")
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
    from_user = db.ReferenceProperty( db.Model, collection_name="from_relationships" )
    to_user   = db.ReferenceProperty( db.Model, default = None, collection_name="to_relationships" )
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

