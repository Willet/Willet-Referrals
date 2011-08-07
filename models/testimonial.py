# Testimonial model
# stores text from giving us feedback via site.

__all__ = [
    'Testimonial'
]

import logging
from google.appengine.api import memcache
from google.appengine.ext import db

from models.model import Model
from util.helpers import generate_uuid

class Testimonial(Model):
    """Model storing the data for a client's sharing campaign"""
    uuid     = db.StringProperty( indexed = True )
    created  = db.DateTimeProperty(auto_now_add=True)
    message  = db.StringProperty(multiline=True)
    user     = db.ReferenceProperty( db.Model, collection_name = 'user_testimonials' )
    campaign = db.ReferenceProperty( db.Model, collection_name = 'campaign_testimonials' )
    
    def __init__(self, *args, **kwargs):
        self._memcache_key = kwargs['uuid'] if 'uuid' in kwargs else None 
        super(Testimonial, self).__init__(*args, **kwargs)
    
    @staticmethod
    def _get_from_datastore( uuid ):
        """Datastore retrieval using memcache_key"""
        return db.Query(Testimonial).filter('uuid =', uuid).get()

def create_testimonial( user,  message, link ):
    campaign = link.campaign

    # Create the default share text
    if campaign.target_url in campaign.share_text:
        share_text = campaign.share_text.replace( campaign.target_url, link.get_willt_url() )
    else:
        share_text = campaign.share_text + " " + link.get_willt_url()

    # If the testimonial is not the same as the share text:
    if message != share_text:
        # Make a new testimonial
        uuid = generate_uuid(16)
        t = Testimonial( key_name = uuid,
                         uuid = uuid,
                         user=user,
                         message=message,
                         campaign=campaign )
        # Save it!
        t.put()
