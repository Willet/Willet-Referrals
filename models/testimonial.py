# Testimonial model
# stores text from giving us feedback via site.

__all__ = [
    'Testimonial'
]

import logging
from google.appengine.api import memcache
from google.appengine.ext import db

from models.model import Model

class Testimonial(Model):
    """Model storing the data for a client's sharing campaign"""
    created = db.DateTimeProperty(auto_now_add=True)
    message = db.StringProperty(multiline=True)
    client  = db.ReferenceProperty( db.Model, collection_name = 'testimonial' )
    
    def __init__(self, *args, **kwargs):
        self._memcache_key = kwargs['created'] if 'created' in kwargs else None 
        super(Testimonial, self).__init__(*args, **kwargs)
    
    @staticmethod
    def _get_from_datastore(created):
        """Datastore retrieval using memcache_key"""
        return db.Query(Testimonial).filter('created =', created).get()
