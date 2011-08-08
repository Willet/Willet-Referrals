#!/usr/bin/python

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc"

import logging, re

from google.appengine.api import urlfetch
from django.utils import simplejson as json
from google.appengine.api import memcache
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

from models.user import User, get_user_by_twitter, get_or_create_user_by_twitter, get_user_by_uuid
from models.campaign import Campaign, ShareCounter, get_campaign_by_id
from models.link import *
from util.helpers import *
from util.urihandler import URIHandler
from util.consts import *

##-----------------------------------------------------------------------------##
##------------------------- The Dos -------------------------------------------##
##-----------------------------------------------------------------------------##

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
                                 payload = payload,
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
                                 payload = payload,
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
            for i in loaded_json:
                logging.info("%r %s"% (i, 'about.me' in i) )
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

            user.put()

##-----------------------------------------------------------------------------##
##------------------------- The URI Router ------------------------------------##
##-----------------------------------------------------------------------------##
def main():
    application = webapp.WSGIApplication([
        (r'/klout', QueryKloutAPI),
        (r'/socialGraphAPI', QueryGoogleSocialGraphAPI),
        ], debug=USING_DEV_SERVER)
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
