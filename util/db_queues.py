#!/usr/bin/python

__author__      = "Sy Khader"
__copyright__   = "Copyright 2011, The Willet Corportation"


from google.appengine.api import urlfetch, memcache, users, taskqueue
from google.appengine.ext.db import GqlQuery
from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

from models.user import User
from models.campaign import Campaign, ShareCounter, get_campaign_by_id
from models.link import *
from util.helpers import *
from util.consts import *

class StartReferenceCheck( webapp.RequestHandler):
    """The handler that will be invokved by the cron job that will
       initiate the db.model user reference check"""

    def get(self):
        models = ['Link']

        for model in models:
            q = "SELECT * FROM " + model
            model_members = GqlQuery(q)
            for mm in model_members:
                taskqueue.add(url='/CheckRef', params={'key': mm.key()})


class CheckReferences( webapp.RequestHandler ):
    """This handler is passed an entity and checks it to ensure
        that the user atached to it still exist.

        This handler currently deletes tweets with users that are dead
        references""" 

    def post(self):
        references = ['_user']
        entity_key = self.request.get('key')
        entity = db.get(entity_key)
        if entity:
            for attr, value in entity.__dict__.iteritems():
                if attr in references:
                    entity_property = getattr(entity, attr)
                    if entity_property is not None and\
                        db.get(entity_property) is None:
                        setattr(entity, attr, None)
                        entity.delete()
                        #entity.put()


def main():
    application = webapp.WSGIApplication([
        (r'/StartRefCheck', StartReferenceCheck),
        (r'/CheckRef', CheckReferences)
        ], debug=USING_DEV_SERVER)
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
