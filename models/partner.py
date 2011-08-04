# Partner model
# dump of data from /partner page

__all__ = [
    'Partner'
]

import logging

from google.appengine.api import memcache
from google.appengine.ext import db
from models.model import Model



class Partner(db.Model):
    """Model storing the data for a client's sharing campaign"""
    created = db.DateTimeProperty(auto_now_add=True)
    name    = db.StringProperty()
    message = db.StringProperty()
    email   = db.StringProperty()
    client  = db.ReferenceProperty( db.Model, collection_name = 'partners' )


    def __init__(self, *args, **kwargs):
       self._memcache_key = kwargs['client'] if 'client' in kwargs else None 
       super(Partner, self).__init__(*args, **kwargs)

    @staticmethod
    def _get_from_datastore(client):
       """Datastore retrieval using memcache_key"""
       return db.Query(Partner).filter('client =', client).get()