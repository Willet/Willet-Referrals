import logging
import time

from datetime import timedelta
from google.appengine.api import memcache, datastore_errors, taskqueue
from google.appengine.datastore import entity_pb
from google.appengine.ext import db




class Model(db.Model):
    """A generic extension of db.Model"""
    
    def put(self):
        """Stores model instance in memcache and database"""
        key = '%s-%s' % (self.__class__.__name__.lower(), self._memcache_key)
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
            memcache.set(key, db.model_to_protobuf(self).Encode())
            
        return True

    def hardPut( self ):
        logging.debug("PUTTING %s" % self.__class__.__name__)
        self.validateSelf( )
        db.put( self )
        
    def validateSelf( self ):
        pass # Fill in in sub class!!

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
                memcache.set(key, db.model_to_protobuf(entity).Encode())
            return entity
        else:
            logging.debug('Model::get(): %s found in memcache!' % key)
            return db.model_from_protobuf(entity_pb.EntityProto(data))
# end class
