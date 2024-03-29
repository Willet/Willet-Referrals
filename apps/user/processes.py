#!/usr/bin/env python

"""
user processes!
"""

import hashlib, logging, urllib, urllib2, uuid, re, Cookie, os

from datetime import datetime
from django.utils import simplejson as json

from google.appengine.api import memcache, taskqueue, urlfetch
from google.appengine.ext import db, webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

from apps.app.models import App, ShareCounter
from apps.email.models import Email
from apps.link.models import *
from apps.user.models import *
from apps.user.models import EmailModel

from util.consts import *
from util.helpers import *
from util.urihandler import URIHandler


class FetchFacebookData(URIHandler):
    """Fetch facebook information about the given user"""
    def post(self):
        def txn(user):
            if user:
                url = FACEBOOK_QUERY_URL + rq_vars['fb_id'] + "?fields=id,name"+\
                    ",gender,username,timezone,updated_time,verified,birthday"+\
                    ",email,interested_in,location,relationship_status,religion"+\
                    ",website,work&access_token=" + user.get_attr('fb_access_token', '')
                fb_response = json.loads(urllib.urlopen(url).read())
                logging.info(fb_response)
                target_data = [
                    'first_name',
                    'last_name',
                    'gender',
                    'verified',
                    'timezone',
                    'email',
                    'name',
                    'username'
                ]
                collected_data = {}
                for td in target_data:
                    if fb_response.has_key(td):
                        collected_data['fb_%s' % td] = unicode(fb_response[td])
                try:
                    collected_data['facebook_profile_pic'] = '%s%s/picture' % (
                        FACEBOOK_QUERY_URL,
                        rq_vars['fb_id']
                    )
                except:
                    logging.info('user does not have a facebook username')

                user.update(**collected_data)
            else:
                pass
            return user
        rq_vars = get_request_variables(['fb_id', 'user_uuid'], self)
        logging.info("Grabbing user data for id: %s %s" % (
            rq_vars['fb_id'],
            rq_vars['user_uuid']
        ))
        user = User.all().filter('uuid =', rq_vars['user_uuid']).get()
        #user = User.all().filter('fb_identity =', rq_vars['fb_id']).get()
        result_user = db.run_in_transaction(txn, user)

        # HACK to fix email.
        # We cannot run queries in this transaction on EmailModel class.
        # If we want to setup the email correctly, we have to fix it here.
        if hasattr(result_user, 'fb_email'):
            logging.info("DOING EMAIL STUFF: %s" % result_user.get_attr('fb_email'))
            email = result_user.fb_email
            EmailModel.get_or_create(result_user, email)

            delattr(result_user, 'fb_email')
            result_user.put_later()
        elif result_user is None:
            logging.debug ("result_user is None!")

        logging.info("done updating")


class FetchFacebookFriends(URIHandler):
    """Fetch and save the facebook friends of a given user"""
    def get(self):
        def txn(user):
            if user:
                friends = []
                url = FACEBOOK_QUERY_URL + rq_vars['fb_id'] + "/friends"+\
                    "?access_token=" + user.get_attr('fb_access_token')
                fb_response = json.loads(urllib.urlopen(url).read())
                if fb_response.has_key('data'):
                    for friend in fb_response['data']:
                        willet_friend = User.get_or_create_by_facebook(friend['id'],
                            name=friend['name'], would_be=True)
                        friends.append(willet_friend.key())
                    user.update(fb_friends=friends)
            return fb_response

        rq_vars = get_request_variables(['fb_id'], self)
        user = User.all().filter('fb_identity =', rq_vars['fb_id'])
        fb_response = db.run_in_transaction(txn, user)
        logging.info(fb_response)


class QueryGoogleSocialGraphAPI(URIHandler):
    def get(self):
        id = self.request.get('id')
        uuid = self.request.get('uuid')
        user = User.get(uuid)

        if user == None:
            return # Bad data, just exit

        result = urlfetch.fetch("%sq=%s" % (GOOGLE_SOCIAL_GRAPH_API_URL, id))

        if result.status_code != 200:
            logging.info("Social Graph API for %s failed" % id)
        else:
            loaded_json = json.loads(result.content)

            logging.info("Social Graph back: %r" % loaded_json)

            for i, value in loaded_json.iteritems():

                # Social Networks
                if 'about.me' in i:
                    user.about_me_url = i
                elif 'facebook' in i:
                    user.fb_identity = i
                elif 'twitter' in i:
                    tmp = i.split('/')
                    user.twitter_handle = tmp[ len(tmp) - 1 ]
                elif 'linkedin' in i:
                    user.linkedin_url = i
                elif 'quora' in i:
                    user.quora_url = i
                elif 'youtube' in i:
                    user.youtube_url = i

                # Other Stuff
                elif 'openid' in i:
                    user.openid_url = i
                elif 'github' in i:
                    user.github_url = i

                # Profiles
                elif 'aol' in i or 'aim' in i:
                    user.aol_profile_url = i
                elif 'profiles.google' in i:
                    user.google_profile_url = i
                elif 'crunchbase' in i:
                    user.crunchbase_url = i

                # Photos
                elif 'flickr' in i:
                    user.flickr_url = i

                # Blogs
                elif 'blogspot' in i:
                    user.blogspot_url = i
                elif 'blogger' in i:
                    user.blogger_url = i
                elif 'tumblr' in i or 'tumblelog' in i:
                    user.tumblr_url = i
                elif 'typepad' in i:
                    user.typepad_url = i
                elif 'posterous' in i:
                    user.posterous_url = i
                elif 'wordpress' in i:
                    user.wordpress_url = i
                elif 'blog' in i:
                    user.blog_url = i

                # News Sites
                elif 'google.com/reader' in i:
                    user.google_reader_url = i

                else:
                    user.other_data.append(i)

                unpacker(value['attributes'], user)

            user.put_later()

# Should this utility function be defined here?
def unpacker(obj, user):
    r = []
    logging.info('v:%r'% obj)
    for k, v in obj.iteritems():

        logging.info("k:%s v:%r" % (k, v))
        if 'location' in k:
            user.location = v
        elif 'fn' == k:
            user.full_name = v

            tmp = v.split(' ')
            l = len(tmp)
            if l >= 2:
                user.first_name = tmp[0]
                user.last_name = tmp[l-1]
        elif 'photo' in k:
            user.photo = v

        elif isinstance(v, object) and not isinstance(v, str)\
            and not isinstance(v, int):
            try:
                r += unpacker(v, user)
            except:
                continue
        else:
            continue
    return r


class UpdateEmailAddress(URIHandler):
    """Allows updates to the current user.

    New: allows update of the name attribute as well.
    New: allows update of FB access token (deprecated) as well.
    """
    def post(self):
        user = User.get(self.request.get('user_uuid'))
        if not user:  # null-cookie'd
            self.error(404)
            return

        email = self.request.get('email')
        if email:
            user.update(email=email)

        name = self.request.get('name')
        if name:
            user.update(full_name=name)

        access_token = self.request.get('accessToken')
        if access_token:
            user.update(fb_access_token=access_token)

        fb_user_id = self.request.get('fbUserId')
        if fb_user_id:
            user.update(fb_identity=fb_user_id)