#!/usr/bin/python

# Model - a base model for all of our models
# ObjectListProperty - list of objects, transparently serialized in the db

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2012, Willet, Inc"

import logging
import time
from datetime import timedelta

from django.utils import simplejson
    
from google.appengine.api import memcache, datastore_errors, taskqueue
from google.appengine.datastore import entity_pb
from google.appengine.ext import db
from google.appengine.ext import deferred
from google.net.proto import ProtocolBuffer

from util.consts import MEMCACHE_TIMEOUT

def async_model_put(model):
    """ Helper method to write and memcache models asynchronously.
        Deferred can't use a bound method (not pickle-able), so we need this function
    """
    try:
        db.put(model)
        key = model.get_key()
        memcache.set(key, db.model_to_protobuf(model).Encode(), time=MEMCACHE_TIMEOUT)
    except Exception, e:
        logging.error('Error saving model %s: %s' % (model, e), exc_info=True)
    return True


class Model(db.Model):
    """A generic extension of db.Model which transparently supports memcaching"""

    # Unique identifier for memcache and DB key
    uuid = db.StringProperty(indexed=True)
    
    @classmethod
    def _get_from_datastore(cls, memcache_key):
        """ Datastore retrieval using memcache_key """
        raise NotImplementedError('_get_from_datastore should be implemented by <%s.%s>' % (self.__class__.__module__, self.__class__.__name__))

    # DB fields by which this object will be memcached.
    # Subclasses can add their own fields.
    # Memcaching with non-unique fields yields unexpected results!
    # Failure to cache a given field will raise a warning.
    _memcache_fields = []

    def _validate_self(self):
        ''' All Model subclasses containing a _validate_self function
            will be checked for errors when they are put().
            This function can either raise an exception when its contents are 
            deemed invalid, or automatically correct its contents.
            
            Example with exception raised:
            def _validate_self(self):
                if not (self.vote == 'yes' or self.vote == 'no'):
                    raise Exception("Vote type needs to be yes or no")
            
            Example with data correction:
            def _validate_self(self):
                self.url = get_shopify_url(self.url)
        '''
        # Subclasses must override this
        raise NotImplementedError('_validate_self should be implemented by <%s.%s>' % (self.__class__.__module__, self.__class__.__name__))

    # Database methods -----------------------------------------------------------------
    def put(self):
        """Stores model instance in memcache and database"""
        try:
            self._validate_self()
        except NotImplementedError, e:
            logging.error(e)

        self._put()

    def put_later(self):
        """Asynchronously stores model instance in memcache and database"""
        try:
            self._validate_self()
        except NotImplementedError, e:
            logging.error(e)
        
        # Immediately add to memcache so requests get new state
        key = self.get_key()
        memcache.set(key, db.model_to_protobuf(self).Encode(), time=MEMCACHE_TIMEOUT)

        # Memcache will be updated after model is given datastore key
        deferred.defer(async_model_put, self, _queue='model-deferred')

        return True

    def _put(self):
        ''' Helper method to write and memcache models.'''
        try:
            db.put(self)
            key = self.get_key()
            memcache.set(key, db.model_to_protobuf(self).Encode(), time=MEMCACHE_TIMEOUT)
        except Exception, e:
            logging.error('Error saving model <%s:%s>: %s' % (self.__class__.__module__,self.__class__.__name__, e), exc_info=True)
        return True

    # Storage key methods -------------------------------------------------------------------
    def get_key(self):
        if hasattr(self, 'memcache_class'):
            return '%s-%s' % (self.memcache_class, self._memcache_key)
        else:
            return '%s-%s' % (self.__class__.__name__.lower(), self._memcache_key)

    @classmethod
    def build_key(cls, memcache_key):
        if hasattr(cls, 'memcache_class'):
            key = '%s-%s' % (cls.memcache_class, memcache_key)
        else:
            key = '%s-%s' % (cls.__name__.lower(), memcache_key)
        return key
    
    # Retrievers --------------------------------------------------------------------------
    @classmethod
    def get(cls, memcache_key):
        """ Checks memcache for model before hitting database

        Each class must define a _get_from_datastore
        """
        obj = None
        key = cls.build_key(memcache_key)
        data = memcache.get(key)

        if data:
            try:
                obj = db.model_from_protobuf(entity_pb.EntityProto(data))
            except ProtocolBuffer.ProtocolBufferDecodeError, e: # fails with ProtocolBuffer.ProtocolBufferDecodeError if data is not unserializable
                pass # Primary key miss
        
        if data and not obj:
            try:
                data = memcache.get(data) # look deeper into memcache
                obj = db.model_from_protobuf(entity_pb.EntityProto(data))
            except ProtocolBuffer.ProtocolBufferDecodeError, e: # fails with ProtocolBuffer.ProtocolBufferDecodeError if data is not unserializable
                pass # Secondary key miss
        
        if not data:
            # object was not found in memcache
            obj = cls._get_from_datastore(memcache_key)

        # Throw everything in the memcache when you pull it - it may never be saved
        if obj:
            obj._memcache() # update memcache
        else:
            # logging.warn ('Memcache AND DB miss for %s!' % key)
            pass
            
        return obj
    
    def _memcache(self):
        ''' save object into the memcache with primary and secondary cache keys.
            primary keys point to the object; secondary keys point to the primary key.
        '''
        sec_keys = []
        try:
            key = self.get_key()
            for field in self._memcache_fields: # get secondary keys to point to primary key
                if getattr (self, field, None): # if this object's given property has a non-null value
                    # e.g. sibt-http://ohai.ca if SIBT specifies memcache by a store URL field
                    sec_keys.append(self.build_key (str (getattr (self, field))))
            
            # that is, {sec_key1: primary_key, sec_key2: primary_key, sec_key3: primary_key, primary_key: object_serial}
            cache_keys_dict = dict(zip(sec_keys, [key] * len(sec_keys)))
            cache_keys_dict[key] = db.model_to_protobuf(self).Encode() # add primary key
            
            try:
                memcache.set_multi (cache_keys_dict, time=MEMCACHE_TIMEOUT)
            except Exception, e:
                logging.warn ("Failed to memcache object by custom key: %s" % e, exc_info=True)

        except Exception, e:
            logging.error("Error setting memcache for %s (%d secondary keys: %r)" % (e, self, len(self._memcache_fields), self._memcache_fields), exc_info=True)
# end class

class ObjectListProperty(db.ListProperty):
    """A property that stores a list of serializable class instances.
    Serialization / deserialization are done transparently when putting
    and getting.  This is a paramaterized property; the parameter must be a
    class with serializable members.

    ObjectListProperty optionally uses 'serialize' and 'deserialize' methods
    from the item class if they exist, otherwise a JSON representation of the
    item's internal dict is used.  These methods should be implemented if the
    class has attributes that are not builtin types.
    
    Note: can store serialized objects of strings up to 500 characters in 
    length. For longer strings, change line with #! comment: 'str' ->
     'db.Text' and handle with encoding / decoding
    
    Example:
    
    class Record():
        def __init__(self, who, timestamp=None):
            self.who = who.key() if hasattr(who, 'key') else who # Some user model
            self.timestamp = timestamp if timestamp else time.time()
    
    class Usage_Tracker(db.Model):
        records = ObjectListProperty(Record, indexed=False)

    """
    def __init__(self, cls, *args, **kwargs):
        """Construct ObjectListProperty
        
        Args:
            cls: Class of objects in list
            *args: Optional additional arguments, passed to base class
            **kwds: Optional additional keyword arguments, passed to base class
        """
        self._cls = cls

        super(ObjectListProperty, self).__init__(str, *args, **kwargs) #!

    def __repr__(self):
        return '<%s.%s at %s\n%s> containing <%s.%s>' % (self.__class__.__module__,
                                        self.__class__.__name__,
                                        hex(id(self)), 
                                        str('\n '.join('%s : %s' % (k, repr(v)) 
                                            for (k, v) in self.__dict.iteritems())),
                                        self._cls.__class__.__module__,
                                        self._cls.__class__.__name__)
    
    def validate_list_contents(self, value):
        """Validates that all items in the list are of the correct type.
        
        Returns:
            The validated list.
        
        Raises:
            BadValueError if the list has items are not instances of the
            cls given to the constructor.
        """
        for item in value:
            if not isinstance(item, self._cls):
                raise db.BadValueError('%s Items in %s must all be of type %r' % (debug_info(), self.name, self._cls) )
        return value
    
    def get_value_for_datastore(self, model_instance):
        """Serialize list to send to datastore.
        
        Returns:
            validated list appropriate to save in the datastore.
        """
        if hasattr(self._cls, 'serialize') and callable(getattr(self._cls, 'serialize')):
            def item_to_string(i):
                return i.serialize()
        else:
            def item_to_string(i):
                return simplejson.dumps(i.__dict__)

        obj_list = self.__get__(model_instance, model_instance.__class__)
        if obj_list is not None and type(obj_list) is list:
            db_list = []

            for obj in obj_list:

                if isinstance(obj, self._cls):
                    obj_str = item_to_string(obj)

                    if not len(obj_str) > 500:
                        db_list.append(obj_str)
                    else:
                        raise OverflowError('%s %s does not support object serialization \
                                             over 500 characters in length.  Substitute str representation \
                                             for db.Text in %s.%s' % (debug_info(),
                                                                      self.name,
                                                                      self.__class__.__module__,
                                                                      self.__class__.__name__))    
            return db_list
        else:
            return []
    
    def make_value_from_datastore(self, db_list):
        """Deserialize datastore representation to list
        
        Returns:
            The value converted for use as a model instance attribute.
        """
        if hasattr(self._cls, 'deserialize') and callable(getattr(self._cls, 'deserialize')):
            def string_to_item(s):
                return self._cls.deserialize(s)
        else:
            def string_to_item(s):
                return self._cls(**(simplejson.loads(s)))

        if db_list is not None and type(db_list) is list:
            return [ string_to_item(value) for value in db_list ]
        else:
            return []
# end class

