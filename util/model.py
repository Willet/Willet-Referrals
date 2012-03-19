import logging
import time
from datetime import timedelta

from django.utils import simplejson
    
from google.appengine.api import memcache, datastore_errors, taskqueue
from google.appengine.datastore import entity_pb
from google.appengine.ext import db

from util.consts import MEMCACHE_TIMEOUT

class Model(db.Model):
    """A generic extension of db.Model"""

    # Unique identifier for memcache and DB key
    uuid = db.StringProperty( indexed = True )
    
    def put(self):
        """Stores model instance in memcache and database"""
        key = self.get_key()
        logging.debug('Model::put(): Saving %s to memcache and datastore.' % key)
        timeout_ms = 100
        while True:
            logging.debug('Model::put(): Trying %s.put, timeout_ms=%i.' % (self.__class__.__name__.lower(), timeout_ms))
            try:
                self.hardPut() # Will validate the instance.
            except datastore_errors.Timeout:
                thread.sleep(timeout_ms)
                timeout_ms *= 2
            else:
                break
        # Memcache *after* model is given datastore key
        if self.key():
            logging.debug('setting new memcache entity: %s' % key)
            memcache.set(key, db.model_to_protobuf(self).Encode(), time=MEMCACHE_TIMEOUT)
            
        return True

    def hardPut( self ):
        logging.debug("PUTTING %s" % self.__class__.__name__)
        db.put(self)
        
    def validateSelf( self ):
        pass # Fill in in sub class!!

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
    
    @classmethod
    def get(cls, memcache_key):
        """Checks memcache for model before hitting database
        Each class must have a staticmethod get_from_datastore
        TODO(barbara): Enforce the above statement!!!
        Also, should it be: get_from_datastore OR _get_from_datastore?
        """
        key = cls.build_key(memcache_key)
        logging.debug('Model::get(): Pulling %s from memcache.' % key)
        data = memcache.get(key)
        if not data:
            logging.debug('Model::get(): %s not found in memcache, hitting datastore.' % key)
            entity = cls._get_from_datastore(memcache_key)
            # Throw everything in the memcache when you pull it - it may never be saved
            if entity:
                logging.debug('setting new memcache entity: %s' % key)
                memcache.set(key, db.model_to_protobuf(entity).Encode(), time=MEMCACHE_TIMEOUT)
            return entity
        else:
            logging.debug('Model::get(): %s found in memcache!' % key)
            return db.model_from_protobuf(entity_pb.EntityProto(data))

    @classmethod
    def get_by (cls, field, value):
        ''' supply field corresponding to the object's property
            and required value, e.g. product_id, '1234'
            and this function will return the first match, first by looking for
            it in the memcache, then by DB query.
        '''
        data = memcache.get('%s-%s:%s' % (cls.__name__.lower(), field, str (value)))
        if data:
            obj = db.model_from_protobuf(entity_pb.EntityProto(data))
        else:
            obj = cls.all().filter('%s =' % field, value).get()

        return product
    
    '''def memcache_by (self, field):
        """ supply field corresponding to the object's property
            and this function will cache the object based on its class name and
            the value of that field.
        """
        if hasattr(self, field):
            return memcache.set(
                    '%s-%s:%s' % (type(self).lower(), field, self.field),
                    db.model_to_protobuf(self).Encode(),
                    time=MEMCACHE_TIMEOUT)
        return False
    '''

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
