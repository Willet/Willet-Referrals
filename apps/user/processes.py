#!/usr/bin/env python

"""
campaign processes!
"""

import hashlib, logging, urllib, urllib2, uuid

from datetime import datetime
from django.utils import simplejson as json

from google.appengine.api import memcache, taskqueue, urlfetch
from google.appengine.ext import db, webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_appfrom apps.user.models import * 

from apps.user.models import *

from util.consts import *
from util.emails import Email
from util.helpers import *
from util.urihandler import URIHandler

class FetchFacebookData(webapp.RequestHandler):
    """Fetch facebook information about the given user"""
    def post(self):
        rq_vars = get_request_variables(['fb_id'], self)
        logging.info("Grabbing user data for id: %s" % rq_vars['fb_id'])
        def txn():
            user = get_user_by_facebook(rq_vars['fb_id'])
            if user:
                url = FACEBOOK_QUERY_URL + rq_vars['fb_id'] + "?fields=id,name"+\
                    ",gender,username,timezone,updated_time,verified,birthday"+\
                    ",email,interested_in,location,relationship_status,religion"+\
                    ",website,work&access_token=" + getattr(user, 'facebook_access_token')
                fb_response = json.loads(urllib.urlopen(url).read())
                logging.info(fb_response)
                target_data = ['first_name', 'last_name', 'gender', 'verified',
                    'timezone', 'email'] 
                collected_data = {}
                for td in target_data:
                    if fb_response.has_key(td):
                        collected_data['fb_'+td] = fb_response[td]
                user.update(**collected_data)
        db.run_in_transaction(txn)
        logging.info("done updating")

            
class FetchFacebookFriends(webapp.RequestHandler):
    """Fetch and save the facebook friends of a given user"""
    def get(self):
        rq_vars = get_request_variables(['fb_id'], self)
        def txn():
            user = get_user_by_facebook(rq_vars['fb_id'])
            if user:
                friends = []
                url = FACEBOOK_QUERY_URL + rq_vars['fb_id'] + "/friends"+\
                    "?access_token=" + getattr(user, 'fb_access_token')
                fb_response = json.loads(urllib.urlopen(url).read())
                if fb_response.has_key('data'):
                    for friend in fb_response['data']:
                        willet_friend = get_or_create_user_by_facebook(friend['id'],
                            name=friend['name'], would_be=True)
                        friends.append(willet_friend.key())
                    user.update(fb_friends=friends)
        db.run_in_transaction(txn)
        logging.info(fb_response)


