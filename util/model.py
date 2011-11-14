import logging
import time

from datetime import timedelta
from google.appengine.api import memcache, datastore_errors, taskqueue
from google.appengine.datastore import entity_pb
from google.appengine.ext import db

from util.consts import MEMCACHE_TIMEOUT

class Model(db.Model):
    """A generic extension of db.Model"""
    
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
# end class



class ObjectListProperty(db.ListProperty):
    """A property that stores a list of serializable class instances
    
    This is a paramaterized property; the parameter must be a class with
    'serialize' and 'deserialize' methods, and all items must conform to
    this type
    
    Will store serialized objects of strings up to 500 characters in length. For
    longer strings, change line with #! comment: 'str' -> 'db.Text' and deal 
    with encoding / decoding
    
    Example:
    
    class Record:
        def __init__(self, who, timestamp=None):
            self.who = who.key() if hasattr(who, 'key') else who # Some user model
            self.timestamp = timestamp if timestamp else time.time()
        
        def serialize(self):
            return "%s@%s" % (str(self.who), str(self.time))
        
        @classmethod
        def deserialize(cls, value):
            [ who, timestamp ] = value.split('@', 1)
            return cls(who= db.Key(who), timestamp= float(timestamp))
    
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
        # Ensure cls has serial / deserial methods
        if not hasattr(cls, 'serialize') or not hasattr(cls, 'deserialize'):
            raise ValueError('%s ObjectListProperty requires properties with \'serialize\' and \'deserialize\' methods' % debug_info() )
        self._cls = cls
        super(ObjectListProperty, self).__init__(str, *args, **kwargs) #!
    
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
                raise BadValueError('%s Items in %s must all be of type %r' % (debug_info(), self.name, self._cls))
        return value
    
    def get_value_for_datastore(self, model_instance):
        """Serialize list to send to datastore.
        
        Returns:
            validated list appropriate to save in the datastore.
        """
        obj_list = self.__get__(model_instance, model_instance.__class__)
        if obj_list is not None and type(obj_list) is list:
            db_list = []
            for obj in obj_list:
                if isinstance(obj, self._cls):
                    obj_str = obj.serialize()
                    if len(obj_str) > 500:
                        raise OverflowError('%s ObjectListProperty does not support strings over 500 characters in length' % debug_info())
                    db_list.append(obj_str)
            return db_list
        else:
            return []
    
    def make_value_from_datastore(self, db_list):
        """Deserialize datastore representation to list
        
        Returns:
            The value converted for use as a model instance attribute.
        """
        if db_list is not None and type(db_list) is list:
            return [ self._cls.deserialize(value) for value in db_list ]
        else:
            return []
