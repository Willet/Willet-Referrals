#!/usr/bin/env python

import logging
import datetime
import random
import inspect

from decimal import *

from google.appengine.api import taskqueue
from google.appengine.ext import deferred 
from google.appengine.ext import db
from google.appengine.datastore import entity_pb
from google.appengine.api import memcache
from google.appengine.api.app_identity import get_application_id

from apps.user.models import User

from util.model import Model
from util.helpers import encode_base62
from util.helpers import url
from util.consts import APP_LIVE, DOMAIN, MEMCACHE_TIMEOUT
from util.memcache_ref_prop import MemcacheReferenceProperty

NUM_SHARDS = 25

def put_link(memcache_key):
    """Deferred task to put a link to datastore"""
    try:
        data = memcache.get(memcache_key)
        if data:
            link = db.model_from_protobuf(entity_pb.EntityProto(data))
            link.put()
            logging.info('deferred link put: %s' % link)
        else:
            logging.info('no data for key: %s' % memcache_key)
    except Exception, e:
        logging.error('error saving link %s: %s' % (memcache_key, e), exc_info=True)

# ------------------------------------------------------------------------------
# Link Class    ----------------------------------------------------------------
# ------------------------------------------------------------------------------
class Link(Model):
    """A tracking link that will be shared by our future Users. A Link keeps 
       track of how many unique clicks it receives"""
       
    # destination of the link, supplied by our clients
    target_url = db.LinkProperty(indexed = True)
    # our unique identifier code for this Link
    willt_url_code = db.StringProperty(indexed = True)
    # our client's app that this link is associated with
    app_ = db.ReferenceProperty(db.Model, collection_name = 'links_', indexed=True) 

    creation_time = db.DateTimeProperty(auto_now_add = True,indexed = True)
    # twitter's identifier for the tweet in question
    tweet_id = db.StringProperty(required=False, default='', indexed=True)
    user = MemcacheReferenceProperty(db.Model, collection_name = 'user_')
    # the string our client supplied us to identify this user with
    supplied_user_id = db.StringProperty(required=False)
    # keep track of our retweets
    retweets = db.ListProperty(str, required=True)
    # the location of the button that spawned this link
    origin_domain = db.StringProperty(str, required=False)
    # facebook's id for the share
    facebook_share_id = db.StringProperty()
    # linkedin's id for the share
    linkedin_share_url = db.StringProperty(required=False, default='', indexed=True)

    # we sent an email!
    email_sent = db.BooleanProperty(required=False, default=False, indexed=True)
    
    def __init__(self, *args, **kwargs):
        self._memcache_key = kwargs['willt_url_code'] if 'willt_url_code' in kwargs else None 
        super(Link, self).__init__(*args, **kwargs)
    
    def _validate_self(self):
        return True

    @staticmethod
    def _get_from_datastore(willt_url_code):
        """Datastore retrieval using memcache_key"""
        return db.Query(Link).filter('willt_url_code =', willt_url_code).get()

    def count_clicks(self):
        """Count this link's sharded clicks"""

        total = memcache.get(self.willt_url_code+"LinkCounter")
        if total is None:
            total = 0
            for counter in LinkCounter.all().\
            filter('willt_url_code =', self.willt_url_code).fetch(25):
                total += counter.count
            memcache.add(key=self.willt_url_code+"LinkCounter", value=total)
        return total

    def add_clicks(self, num):
        """add num clicks to this link's link counter"""

        def txn():
            index = random.randint(0, NUM_SHARDS-1)
            shard_name = self.willt_url_code + str(index)
            counter = LinkCounter.get_by_key_name(shard_name)
            if counter is None:
                counter = LinkCounter(key_name=shard_name, 
                                      willt_url_code=self.willt_url_code)
            counter.count += num
            counter.put()

        db.run_in_transaction(txn)
        memcache.incr(self.willt_url_code+"LinkCounter")

    def increment_clicks(self):
        """Increment this link's click counter"""
        self.add_clicks(1)

    def get_willt_url(self):
        appname = get_application_id() # e.g. brian-willet
        if appname == APP_LIVE:
            # you see, rf.rs links don't actually work unless it is on live server
            return 'http://rf.rs/' + self.willt_url_code
        else:
            # if testing, just output the testing domain
            return 'http://' + DOMAIN + '/' + self.willt_url_code

    def count_retweets(self):
        return len(self.retweets)

    def add_user(self, user):
        if user:
            self.user = user
            self.save()

    # Delete entity and counters
    def purge(self):
        c = self.willt_url_code
        db.delete(self)
        return delete_counters(c)

    def memcache_by_code(self):
        return memcache.set(
                Link.get_memcache_key_for_code(self.willt_url_code), 
                db.model_to_protobuf(self).Encode(), time=MEMCACHE_TIMEOUT)

    @classmethod
    def get_memcache_key_for_code(cls, code):
        return '%s-%s' % (cls.__class__.__name__, code)

    @staticmethod
    def get_by_code(code):
        link = None
        try:
            memcache_key = Link.get_memcache_key_for_code(code)
            data = memcache.get(memcache_key)
            if data:
                link = db.model_from_protobuf(entity_pb.EntityProto(data))
            else:
                logging.info('no data for key: %s' % memcache_key)
        except Exception, e:
            logging.error('error saving link %s: %s' % (memcache_key, e), exc_info=True)
        if not link:
            link = Link.all().filter('willt_url_code =', code).get()
        return link

    @staticmethod
    def create(targetURL, app, domain, user=None, usr=""):
        """Produces a Link containing a unique wil.lt url that will be tracked"""

        logging.debug('called Link.create')
        code = encode_base62(get_a_willt_code())
        logging.debug('got code %s' %  code)
        link = Link(key_name=code,
                    target_url=targetURL,
                    willt_url_code=code,
                    supplied_user_id=usr,
                    app_=app,
                    user=user,
                    origin_domain=domain,
                    retweets=[])

        #link.put()
        link.memcache_by_code()
        deferred.defer(put_link,
                       Link.get_memcache_key_for_code(code),
                       _queue='slow-deferred')
        
        logging.info("Successful put of Link %s" % code)
        return link


# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
class LinkCounter(db.Model):
    """Sharded counter for link click-throughs"""

    willt_url_code = db.StringProperty(indexed=True, required=True)
    count = db.IntegerProperty(indexed=False, required=True, default=0)

def delete_counters(willt_url_code):
    """Delete all the counters belonging to the given willt_url_code"""
    db.delete(LinkCounter.all().filter('willt_url_code =', willt_url_code))
    return True


# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
class CodeCounter(Model):
    """This is a counter we use to generate random, short URLs"""
    # the current count
    count = db.IntegerProperty(indexed=True, required=True)
    # total number of counters
    total_counter_nums = db.IntegerProperty(indexed=False,
                                            required=True,
                                            default=20)
    
    def _validate_self(self):
        # there is not much to check - count can be higher than total_counter_nums
        return True
    
    def get_next(self):
        #c = self.count
        #self.count += self.total_counter_nums
        #self.put()
        #return c
        taskqueue.add(
            url = url('IncrementCodeCounter'),
            params = {
                'count': self.count 
            }
        )
        return self.count
    
    @staticmethod
    def generate_counters (total=20):
        try:
            for i in range(total):
                ac = CodeCounter(
                    count=i,
                    total_counter_nums=total,
                    key_name = str(i)
                )
                ac.put()
            return True
        except db.Timeout, e:
            return False

    def __init__(self, *args, **kwargs):
       self._memcache_key = kwargs['count'] if 'count' in kwargs else None 
       super(CodeCounter, self).__init__(*args, **kwargs)

    @staticmethod
    def _get_from_datastore(count):
       """Datastore retrieval using memcache_key"""
       return db.Query(CodeCounter).filter('count =', count).get()

def get_a_willt_code():
    """Get a counter at random and return an unused code"""
    counter_index = random.randint(0,19)
    counter = CodeCounter.get_by_key_name(str(counter_index))
    if not counter: # links haven't been link/init'ed yet
        CodeCounter.generate_counters()
        # re-get counter object
        counter = CodeCounter.get_by_key_name(str(counter_index))
    c = counter.get_next()
    return c

def increase_counters(n):
    """Increase the total number of code counters"""
    pass

