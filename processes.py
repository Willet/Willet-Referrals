# client models
# data models for our clients and associated methods

__all__ = [
    'Client'
]
import hashlib, logging, urllib, urllib2, uuid

from datetime import datetime
from django.utils import simplejson as json

from google.appengine.api import memcache, taskqueue, urlfetch
from google.appengine.ext import db, webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

from apps.campaign.models import Campaign, ShareCounter, get_campaign_by_id
from apps.client.models import Client
from apps.link.models import Link, LinkCounter
from util.model import Model
from apps.stats.models import Stats
from apps.user.models import User, get_user_by_facebook, get_or_create_user_by_facebook, get_or_create_user_by_email, get_user_by_uuid

from util.consts import *
from util.emails import Email
from util.helpers import *
from util.urihandler import URIHandler



##-----------------------------------------------------------------------------##
##------------------------- The URI Router ------------------------------------##
##-----------------------------------------------------------------------------##
def main():
    application = webapp.WSGIApplication([
        ], debug=USING_DEV_SERVER)
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
