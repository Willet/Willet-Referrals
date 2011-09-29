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

from apps.user.models import *
from apps.app.models import App, ShareCounter, get_app_by_id
from apps.link.models import *
from apps.email.models import Email

from util.consts import *
from util.helpers import *
from util.urihandler import URIHandler

class FetchFacebookData(webapp.RequestHandler):
    """Fetch facebook information about the given user"""
    def post(self):
        def txn(user):
            if user:
                url = FACEBOOK_QUERY_URL + rq_vars['fb_id'] + "?fields=id,name"+\
                    ",gender,username,timezone,updated_time,verified,birthday"+\
                    ",email,interested_in,location,relationship_status,religion"+\
                    ",website,work&access_token=" + user.get_attr('fb_access_token')
                fb_response = json.loads(urllib.urlopen(url).read())
                logging.info(fb_response)
                target_data = [
                    'first_name', 'last_name', 'gender', 'verified',
                    'timezone', 'email'] 
                collected_data = {}
                for td in target_data:
                    if fb_response.has_key(td):
                        collected_data['fb_'+td] = fb_response[td]
                user.update(**collected_data)
            else:
                pass
            return user
        rq_vars = get_request_variables(['fb_id'], self)
        logging.info("Grabbing user data for id: %s" % rq_vars['fb_id'])
        user = User.all().filter('fb_identity =', rq_vars['fb_id']).get()
        result_user = db.run_in_transaction(txn, user)
        logging.info("done updating")

class FetchFacebookFriends(webapp.RequestHandler):
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
                        willet_friend = get_or_create_user_by_facebook(friend['id'],
                            name=friend['name'], would_be=True)
                        friends.append(willet_friend.key())
                    user.update(fb_friends=friends)
            return fb_response 

        rq_vars = get_request_variables(['fb_id'], self)
        user = User.all().filter('fb_identity =', rq_vars['fb_id'])
        fb_response = db.run_in_transaction(txn, user)
        logging.info(fb_response)

class QueryKloutAPI( URIHandler ):
    @admin_required
    def get(self, admin):
        logging.info("KLOUT: MEMCAHCE")
        memcache.flush_all()
        self.response.out.write('<html><body><h1>Memcached flushed</h1></body></html>')
    
    @admin_required
    def post( self, admin ):
        twitter_handle = self.request.get( 'twitter_handle' )
        logging.info("Klout: Fetching for twitter: %s" % twitter_handle )
        
        user = get_or_create_user_by_twitter( twitter_handle )
        
        logging.info("Klout: User is %s %s" % (user.get_attr('twitter_name'), user.get_attr('twitter_handle')))

        data = { 'key'   : KLOUT_API_KEY,
                 'users' : twitter_handle }

        #payload = urllib.urlencode( data )

        logging.info("Klout: Fetching user data for %s" % twitter_handle)
        result = urlfetch.fetch( url     = KLOUT_API_URL,
                                 payload = data,
                                 method  = urlfetch.POST,
                                 headers = {'Content-Type': 'application/x-www-form-urlencoded'} )
        
        if result.status_code != 200:
            logging.info("Klout: User data for %s failed %r" % (twitter_handle, result))
        else:
            # Decode data
            dumped = json.loads( result.content )

            if dumped['status'] == 200:
                users = dumped['users']

                for u in users:
                    user.twitter_id = u['twitter_id']
                    try:
                        user.kscore = u['score']['kscore']
                    except:
                        pass
                    try:
                        user.slope = u['score']['slope']
                    except:
                        pass
                    try:
                        user.network_score = u['score']['network_score']
                    except:
                        pass
                    try:
                        user.amplification_score = u['score']['amplification_score']
                    except:
                        pass
                    try:
                        user.true_reach = u['score']['true_reach']
                    except:
                        pass

                    user.put()

        # Now grab topics
        logging.info("Klout: Fetching topics data for %s" % twitter_handle)
        result = urlfetch.fetch( url     = 'http://api.klout.com/1/users/topics.json',
                                 payload = data,
                                 method  = urlfetch.POST,
                                 headers = {'Content-Type': 'application/x-www-form-urlencoded'} )
        
        if result.status_code != 200:
            logging.info("Klout: Topic data for %s failed" % twitter_handle)
        else:
            dumped = json.loads( result.content )
            
            if dumped['status'] == 200:
                users = dumped['users']

                for u in users:
                    user.topics = u['topics']
                    user.put()

class QueryGoogleSocialGraphAPI( URIHandler ):
    def get( self ):
        id   = self.request.get( 'id' )
        uuid = self.request.get( 'uuid' )
        user = get_user_by_uuid( uuid )

        if user == None:
            return # Bad data, just exit

        result = urlfetch.fetch( "%sq=%s" % (GOOGLE_SOCIAL_GRAPH_API_URL, id) )

        if result.status_code != 200:
            logging.info("Social Graph API for %s failed" % id)
        else:
            loaded_json = json.loads( result.content )
            
            logging.info("Social Graph back: %r" % loaded_json)

            for i, value in loaded_json.iteritems():
                
                # Social Networks
                if 'about.me' in i:
                    user.about_me_url = i
                elif 'facebook' in i:
                    user.fb_identity = i
                elif 'twitter' in i:
                    tmp = i.split( '/' )
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

                unpacker( value['attributes'], user ) 

            user.put()

class UpdateTwitterGraph(webapp.RequestHandler):
    """Updates the twitter graph with a user's latest information after
       fresh tweet"""
    def post(self):
        screen_name = self.request.get('handle')
        name        = self.request.get('name')
        followers   = self.request.get('follows')
        profile_pic = self.request.get('img')
        tweet       = self.request.get('tweet')
        willt_url_code = self.request.get('willt_c')
        user        = None
        logging.info("Updating Twitter Graph with: screen_name=%s name=%s fllw=%s pic=%s tweet=%s willt_url_code=%s" % (screen_name, name, followers, profile_pic, tweet, willt_url_code) )

        # create our user
        logging.info("SCREEN NAME %s" % screen_name)
        if len(screen_name) > 0:
            logging.info("Fetching a user for %s" % screen_name)

            # check to see if this user has a referral cookie set
            referrer_code = self.request.cookies.get('referral', None)
            referrer = None
            logging.info(referrer_code)
            if referrer_code:
                referral_link = get_link_by_willt_code(referrer_code)
                if referral_link and referral_link.user:
                    referrer = referral_link.user
            
            user = get_or_create_user_by_twitter(screen_name, name, int(followers), profile_pic, referrer)
            #logging.info("USER NOW %r" % user)
            
            #logging.info("Fetching a link for %s" % willt_url_code)
            link = get_link_by_willt_code(willt_url_code)
            #logging.info("LINK: %r" % link)
            
            #logging.info("Does link have a user? %s %r (it shouldn't have a user here)" % (link.user != None, link.user))
            link.user = user
            link.put()

            #logging.info("Does link have a user? %s %r (should have a user here)" % (link.user != None, link.user))

            #logging.info("Link has a app? %s %r" % (link.app_ != None, link.app_))
            #logging.info("App has %d shares before" % link.app_.get_shares_count())
            link.app_.increment_shares()
            #logging.info("App has %d shares after (Should be before + 1)" % link.app_.get_shares_count())
        else:
            #logging.info("NO TWITTER HANDLE PROVIDED. EXCEPTION")
            raise Exception("No twitter handle provided")

        if len(screen_name) == 0 or user.get_attr('twitter_name') == '' or user.get_attr('twitter_pic_url') == '':
            logging.error("invalid data provided " + str(self.request))
            mail.send_mail(sender="wil.lt error reporting <Barbara@wil.lt>",
                       to="wil.lt tech support <support@wil.lt>",
                       subject="Javascript /t callback error",
                       body= user.get_attr('twitter_handle') + str(self.request))

        # save the tweet text that we received from the @anywhere callback
        # to the Link. It will late be looked up for a tweet id
        logging.info("Tweet: %s" % tweet)
        if len(tweet) > 0:
            t = save_tweet(willt_url_code, tweet, user, link)
                
        self.response.out.write("ok")


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
                user.last_name  = tmp[l-1]
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

class UpdateEmailAddress(webapp.RequestHandler):
    def post( self ):
        user = get_user_by_cookie( self )

        user.update( email=self.request.get('email')
