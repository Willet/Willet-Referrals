#!/usr/bin/python

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc"

import re, urllib

from django.utils import simplejson as json
from google.appengine.api import urlfetch, memcache
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
        """
        q = ShareCounter.all()

        for w in q:
            w.delete()
        return
        q = Tweet.all()
        for w in q:
            w.delete()

        q = CodeCounter.all()
        for w in q:
            w.delete()
        
        return
        #campaign     = get_campaign_by_id( '44436307e138449e' )
        campaign     = get_campaign_by_id( '5a066f533e684705' )

        f = get_or_create_user_by_twitter( 'FJHarris' )
        f.twitter_pic_url = "https://si0.twimg.com/profile_images/534239129/Faceshot_normal.jpg"
        f.twitter_name ="Fraser Harris"
        f.put()
        link1 = create_link(targetURL='http://www.google.com', camp=campaign, usr=f.twitter_handle)
        link1.user = f
        link1.put()
        for i in range(0,27):
            link1.increment_clicks()
        
        w = get_or_create_user_by_twitter( 'FredWilson' )
        w.twitter_pic_url = "https://si0.twimg.com/profile_images/65818181/fredwilson_reasonably_small.jpg"
        w.twitter_name = "Fred Wilson"
        w.put()
        link11 = create_link(targetURL='http://www.google.com', camp=campaign, usr=w.twitter_handle)
        link11.user = w
        link11.put()
        for i in range(0,30):
            link11.increment_clicks()
        b = get_or_create_user_by_twitter( 'BarbaraEMac' )
        b.twitter_pic_url = "https://si0.twimg.com/profile_images/1287339217/180424_763389994397_122604129_43434071_1465064_n_reasonably_small.jpg"
        b.twitter_name = "Barbara Macdonald"
        b.put()
        link4 = create_link(targetURL='http://www.google.com', camp=campaign, usr=b.twitter_handle)
        link4.user = b
        link4.put()
        for i in range(0,40):
            link4.increment_clicks()
        
        p = get_or_create_user_by_twitter( 'PaulG' )
        p.twitter_pic_url = "https://si0.twimg.com/profile_images/1112174290/pg-railsconf_bigger.jpg"
        p.twitter_name = "Paul Graham"
        p.put()
        link7 = create_link(targetURL='http://www.google.com', camp=campaign, usr=p.twitter_handle)
        link7.user = p
        link7.put()
        for i in range(0,19):
            link7.increment_clicks()
        
        m = get_or_create_user_by_twitter( 'MichaelRLitt' )
        m.twitter_pic_url = "https://si0.twimg.com/profile_images/1383573996/Twitter_Bio_reasonably_small.png"
        m.twitter_name = "Michael R. Litt"
        m.put()
        link6 = create_link(targetURL='http://www.google.com', camp=campaign, usr=m.twitter_handle)
        link6.user = m
        link6.put()
        for i in range(0,5):
            link6.increment_clicks()
        
        r = get_or_create_user_by_twitter( 'RossRobinson' )
        r.twitter_pic_url = "https://si0.twimg.com/profile_images/1099232581/g9_reasonably_small.jpg"
        r.twitter_name = "Ross Robinson"
        r.put()
        link3 = create_link(targetURL='http://www.google.com', camp=campaign, usr=r.twitter_handle)
        link3.user = r
        link3.put()
        for i in range(0,10):
            link3.increment_clicks()
        
        g = get_or_create_user_by_twitter( 'GetWillet' )
        g.twitter_pic_url = "https://si0.twimg.com/profile_images/1426560834/logo_blue_reasonably_small.png"
        g.twitter_name = "GetWillet"
        g.put()
        link5 = create_link(targetURL='http://www.google.com', camp=campaign, usr=g.twitter_handle)
        link5.user = g
        link5.put()
        for i in range(0,2):
            link5.increment_clicks()
        
        k = get_or_create_user_by_twitter( 'Kik' )
        k.twitter_pic_url = "https://si0.twimg.com/profile_images/1340561677/logo_twitter_reasonably_small.png"
        k.twitter_name = "Kik"
        k.put()
        link9 = create_link(targetURL='http://www.google.com', camp=campaign, usr=k.twitter_handle)
        link9.user = k
        link9.put()
        for i in range(0,9):
            link9.increment_clicks()
        v = get_or_create_user_by_twitter( 'UWVelocity' )
        v.twitter_pic_url = "https://si0.twimg.com/profile_images/1432494546/vcity2_reasonably_small.png"
        v.twitter_name = "UWVelocity"
        v.put()
        link10 = create_link(targetURL='http://www.google.com', camp=campaign, usr=v.twitter_handle)
        link10.user = v
        link10.put()
        for i in range(0,8):
            link10.increment_clicks()
        """
    
    @admin_required
    def post( self, admin ):
        twitter_handle = self.request.get( 'twitter_handle' )
        logging.info("Klout: Fetching for twitter: %s" % twitter_handle )
        user = get_or_create_user_by_twitter( twitter_handle )
        
        logging.info("Klout: User is %s %s" % (user.twitter_name, user.twitter_handle))

        data = { 'key'   : KLOUT_API_KEY,
                 'users' : twitter_handle }

        payload = urllib.urlencode( data )

        logging.info("Klout: Fetching user data for %s" % twitter_handle)
        result = urlfetch.fetch( url = KLOUT_API_URL,
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
        result = urlfetch.fetch( url = 'http://api.klout.com/1/users/topics.json',
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
    def post( self ):
        id   = self.request.get( 'id' )
        uuid = self.request.get( 'uuid' )
        user = get_user_by_uuid( uuid )

        if user == None:
            return # Bad data, just exitc:w

        logging.info("Fetching Social Graph API for %s" % id)

        data = { 'q' : id }
        payload = urllib.urlencode( data )

        result = urlfetch.fetch( url     = GOOGLE_SOCIAL_GRAPH_API_URL + payload,
                                 method  = urlfetch.GET,
                                 headers = {'Content-Type': 'application/x-www-form-urlencoded'} )

        if result.status_code != 200:
            logging.info("Social Graph API for %s failed" % id)
        else:
            #loaded_json = json.loads( result.content )

            for i in result.content:
                if 'about.me' in i and user.about_me_url == '':
                    user.about_me_url = i
                
                elif 'facebook' in i and user.fb_identity == '':
                    user.fb_identity = i
                
                elif 'twitter' in i and user.twitter_handle == '':
                    tmp = i.split( '/' )
                    user.twitter_handle = tmp[ len(tmp) - 1 ]

            user.put()

##-----------------------------------------------------------------------------##
##------------------------- The URI Router ------------------------------------##
##-----------------------------------------------------------------------------##
def main():
    application = webapp.WSGIApplication([
        (r'/klout', QueryKloutAPI),
        (r'/socialGraphAPI', QueryGoogleSocialGraphAPI,
        ], debug=USING_DEV_SERVER)
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
