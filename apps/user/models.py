#!/usr/bin/env python

# Data models for our Users
# our Users are our client's clients

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc"

import logging
import sys

from django.utils import simplejson

from calendar import monthrange
from datetime import datetime, timedelta, time as datetime_time
from decimal  import *
from time import time
from hmac import new as hmac
from hashlib import sha1
from traceback import print_tb

from google.appengine.api import memcache
from google.appengine.api import urlfetch
from google.appengine.api import taskqueue
from google.appengine.ext import db

import apps.oauth.models
from apps.user_analytics.models import UserAnalytics, UserAnalyticsServiceStats, get_or_create_ua, get_or_create_ss
from apps.email.models    import Email

from util.consts          import FACEBOOK_QUERY_URL, ADMIN_EMAILS, ADMIN_IPS
from util.model           import Model
from util.helpers         import *
from util                 import oauth2 as oauth

# ------------------------------------------------------------------------------
# EmailModel Class Definition --------------------------------------------------
# ------------------------------------------------------------------------------
class EmailModel(Model):
    created = db.DateTimeProperty(auto_now_add=True)
    address = db.EmailProperty(indexed=True)
    user    = db.ReferenceProperty( db.Model, collection_name = 'emails' )
    
    def __init__(self, *args, **kwargs):
        self._memcache_key = kwargs['created'] if 'created' in kwargs else None 
        super(EmailModel, self).__init__(*args, **kwargs)
    
    @staticmethod
    def _get_from_datastore(created):
        """Datastore retrieval using memcache_key"""
        return db.Query(EmailModel).filter('created =', created).get()
    
# Constructor ------------------------------------------------------------------
def create_email_model( user, email ):
    if email != '':
        # Check to see if we have one already
        em = EmailModel.all().filter( 'address = ', email ).get()
        
        # If we don't have this email, make it!
        if em == None:
            em = EmailModel(key_name=email, address=email, user=user )
        
        # TODO: We might need to merge Users here
        if em.user.uuid != user.uuid:
            Email.emailBarbara( "CHECK OUT: %s %s. They might be the same person." % (em.user.uuid, user.uuid) )
            logging.error("CHECK OUT: %s %s. They might be the same person." % (em.user.uuid, user.uuid))
            em.user = user
        
        em.put()
    
# Accessors --------------------------------------------------------------------
def get_emails_by_user( user ):
    return EmailModel.all().filter( 'user =', user )

# ------------------------------------------------------------------------------
# User Class Definition --------------------------------------------------------
# ------------------------------------------------------------------------------
class User( db.Expando ):
    # General Junk
    uuid            = db.StringProperty(indexed = True)
    creation_time   = db.DateTimeProperty(auto_now_add = True)
    #first_name      = db.StringProperty(indexed=False)
    #last_name       = db.StringProperty(indexed=False)
    #about_me_url    = db.LinkProperty( required = False, default = None )
    referrer        = db.ReferenceProperty(db.Model, collection_name='user-referrer') # will be User.uuid
    client          = db.ReferenceProperty(db.Model, collection_name='client_user')
    other_data      = db.StringListProperty()

    # Twitter Junk
    #twitter_handle  = db.StringProperty(indexed = True)
    #twitter_name    = db.StringProperty()
    #twitter_pic_url = db.LinkProperty( required = False, default = None )
    #twitter_followers_count = db.IntegerProperty(default = 0)
    twitter_access_token = db.ReferenceProperty(db.Model, collection_name='twitter-oauth')
    
    # Linkedin Junk 
    # ! See `mappings` in `update_linkedin_info`
    #linkedin_id    = db.StringProperty
    #linkedin_first_name
    #linkedin_last_name
    #linkedin_industry
    #linkedin_...
    linkedin_access_token = db.ReferenceProperty(db.Model, collection_name='linkedin-users')
    
    # Klout Junk
    #twitter_id          = db.StringProperty( indexed = False )
    #kscore              = db.FloatProperty( indexed = False, default = 1.0 )
    #slope               = db.FloatProperty( indexed = False )
    #network_score       = db.FloatProperty( indexed = False )
    #amplification_score = db.FloatProperty( indexed = False )
    #true_reach          = db.IntegerProperty( indexed = False )
    #topics              = db.ListProperty( str, indexed = False )

    # Facebook Junk
    #fb_identity = db.LinkProperty( required = False, indexed = True, default = None )

    # ReferenceProperty
    #emails = db.EmailProperty(indexed=True)
    
    def __init__(self, *args, **kwargs):
        self._memcache_key = kwargs['uuid'] if 'uuid' in kwargs else None 
        
        #if 'email' in kwargs and kwargs['email'] != '':
        #    create_email_model( self, kwargs['email'] )
       
        super(User, self).__init__(*args, **kwargs)
    
    def is_admin( self ):
        emails = get_emails_by_user( self )
        # Filter by user email
        for e in emails:
            if e.address in ADMIN_EMAILS:
                return True

        # Filter by IP
        if hasattr(self, 'ips'):
            for i in self.ips:
                if i in ADMIN_IPS:
                    return True

        return False

    def get_name_or_handle(self):
        name = self.get_handle()
        if name == None:
            name = self.get_full_name()
        return name

    def get_first_name(self):
        fname = None
        if hasattr(self, 'fb_first_name'):
            fname = self.fb_first_name
        elif hasattr(self, 'first_name'):
            fname = self.first_name
        elif hasattr(self, 'linkedin_first_name'):
            fname = self.linkedin_first_name
        elif hasattr(self, 'fb_username'):
            fname = self.fb_username
        else:
            fname = 'a user'
        return fname

    def get_full_name(self, service=None):
        """attempts to get the users full name, with preference to the
            service supplied"""
        fname = None
        if hasattr(self, 't_handle') and service == 'twitter':
            fname = self.twitter_handle
        elif hasattr(self, 'linkedin_first_name') and service == 'linkedin':
            fname = '%s %s' % (
                self.linkedin_first_name, 
                str(self.get_attr('linkedin_last_name'))
            )
        elif hasattr(self, 'fb_first_name') and service == 'facebook':
            fname = '%s %s' % (
                self.fb_first_name,
                str(self.get_attr('fb_last_name'))
            )
        elif hasattr(self, 'fb_name') and service == 'facebook':
            fname = self.fb_name
        elif hasattr(self, 'full_name'):
            fname = self.full_name
        elif hasattr(self, 'first_name'):
            fname = self.first_name
        elif hasattr(self, 'fb_first_name'):
            fname = '%s %s' % (
                self.fb_first_name,
                str(self.get_attr('fb_last_name'))
            )
        elif hasattr(self, 'fb_name'):
            fname = self.fb_name
        elif hasattr(self, 't_handle'):
            fname = self.t_handle
        else:
            fname = self.get_attr('email')
        
        if fname == None or fname == '':
            fname = "a %s user" % (NAME)

        return fname

    def get_handle(self, service=None):
        """returns the name of this user, depends on what service
            they registered with"""
        handle = None
        if hasattr(self, 'twitter_handle') and\
            (service == 'twitter' or service == None):
            handle = self.twitter_handle
        elif hasattr(self, 'linkedin_first_name') and\
            (service == 'linkedin' or service == None):
            handle = self.linkedin_first_name
        elif hasattr(self, 'fb_name') and\
            (service == 'facebook' or service == None):
            handle = self.fb_name
        elif hasattr(self, 'fb_username') and\
            (service == 'facebook' or service == None):
                handle = self.fb_username
        else:
            handle = self.get_attr('email')

        if (handle == None or handle == '') and service != None:
            # if we didn't get a handle for that service, try again
            handle = self.get_handle()
        return handle

    def get_reach(self, service=None):
        """ returns this users social "reach" """
        reach = 0
        # ugly hacks for reach
        if service == 't':
            service = 'twitter'
        elif service == 'f':
            service = 'facebook'
        elif service == 'l':
            service = 'linkedin'

        if hasattr(self, 'titter_followers_count') and service == 'twitter':
            reach += int(self.twitter_followers_count)
        elif hasattr(self, 'linkedin_num_connections') and service == 'linkedin':
            reach += int(self.linkedin_num_connections)
        elif hasattr(self, 'fb_friends') and service == 'facebook':
            if type(self.fb_friends) == type(int()):
                reach += self.fb_friends
            else:
                reach += int(len(self.fb_friends))
        elif service == None or service == 'total':
            reach = self.get_reach('twitter')\
                    + self.get_reach('facebook')\
                    + self.get_reach('linkedin')
        return reach
    
    def update( self, **kwargs ):
        for k in kwargs:
            if k == 'email':
                create_email_model( self, kwargs['email'] )
            elif k == 'twitter_access_token':
                self.twitter_access_token = kwargs['twitter_access_token']
            elif k == 'client':
                self.client = kwargs['client']
            elif k == 'referrer':
                self.referrer = kwargs['referrer']
            elif k == 'ip':
                if hasattr(self, 'ips') and kwargs['ip'] not in self.ips:
                    self.ips.append( kwargs['ip'])
                else: 
                    self.ips = [ kwargs['ip'] ]

            elif kwargs[k] != '' and kwargs[k] != None and kwargs[k] != []:
                #logging.info("Adding %s %s" % (k, kwargs[k]))
                setattr( self, k, kwargs[k] )
        self.put()
        """
        if 'twitter_handle' in kwargs an
            self.twitter_handle = kwargs['twitter_handle']
        
        if 'twitter_name' in kwargs and kwargs['twitter_name'] != '':
            self.twitter_name = kwargs['twitter_name']
        
        if 'twitter_profile_pic' in kwargs and kwargs['twitter_profile_pic'] != '':
            self.twitter_profile_pic = kwargs['twitter_profile_pic']
            
        if 'twitter_follower_count' in kwargs and kwargs['twitter_follower_count'] != None:
            self.twitter_follower_count = kwargs['twitter_follower_count']
            
        if 'fb_identity' in kwargs and kwargs['fb_identity'] != '':
            self.fb_identity = kwargs['fb_identity']
            
        if 'first_name' in kwargs and kwargs['first_name'] != '':
            self.first_name = kwargs['first_name']
        
        if 'last_name' in kwargs and kwargs['last_name'] != '':
            self.last_name = kwargs['last_name']
        
        if 'email' in kwargs and kwargs['email'] != '':
            create_email_model( self, kwargs['email'] )
        
        if 'referrer' in kwargs and kwargs['referrer'] != None and self.referrer == None:
            self.referrer = kwargs['referrer']
        """

    def get_pics(self):
        """ puts the users pics in a list"""
        pics = [] 
        if hasattr(self, 'facebook_profile_pic'):
            pics.append(getattr(self, 'facebook_profile_pic'))
        if hasattr(self, 'twitter_profile_pic'):
            pics.append(getattr(self, 'twitter_profile_pic'))
        if hasattr(self, 'linkedin_picture_url'):
            pics.append(getattr(self, 'linkedin_picture_url'))
        
        return pics 

    def get_attr( self, attr_name ):
        if attr_name == 'email':
            if hasattr(self, 'fb_email'):
                return self.fb_email
            else:
                return self.emails[0].address if self.emails.count() > 0 else ''
        
        if attr_name == 'pic':
            if hasattr(self, 'facebook_profile_pic'):
                return getattr(self, 'facebook_profile_pic')
            elif hasattr(self, 'twitter_profile_pic'):
                return getattr(self, 'twitter_profile_pic')
            elif hasattr(self, 'linkedin_picture_url'):
                return getattr(self, 'linkedin_picture_url')
            elif hasattr(self, 'fb_username'):
                return '%s%s/picture' % (
                    FACEBOOK_QUERY_URL,        
                    getattr(self, 'fb_identity')
                ) 
            else:
                return 'https://si0.twimg.com/sticky/default_profile_images/default_profile_3_normal.png'

        if hasattr( self, attr_name ):
            return getattr( self, attr_name )
    
    def update_twitter_info(self, **kwargs):
        fields = ['twitter_handle', 'twitter_profile_pic', 'twitter_followers_count', 'twitter_name', 'twitter_access_token']
        insertion = {}
        for k in kwargs:
            if k in fields:
                insertion[k] = kwargs[k]
        self.update(**insertion)
   
    def compute_analytics(self, scope='day', period_start=datetime.today()):
        """computes analytics for this user on this scope"""
        midnight = datetime_time(0)
        period_start = period_start.combine(period_start.date(), midnight)
        if scope == 'day':
            # yesterday
            period_start -= timedelta(days=1)
            period_end = period_start + timedelta(days=1)
        elif scope == 'week':
            # this gets the day of the week, monday=0, sunday=6
            # we want the stats for a full week, so we make sure
            # we are on the first day of the week (monday, 0)
            start_dow = period_start.weekday()
            delta = timedelta(days=start_dow)
            
            period_start -= (delta + timedelta(days=7))

            # now we need the end of the period, 7 days later
            delta = timedelta(days = 7)
            period_end = period_start + delta
        else:
            # we are on the month scope
            # make sure we start on day 1 of the month
            # this is not zero indexed, so we are going to
            # subtract 1 from this value, so that if we are on
            # day 1, we don't timedelta subtract 1...
            # ... it makes sense if you think about it
            month = period_start.month
            year = period_start.year
            if month - 1 == 0:
                month = 12
                year -= 1
            
            period_start.replace(year=year, month=month, day=1)

            # monthrange returns a tuple of first weekday of the month
            # and the number of days in this month, so (int, int)
            # we take the second value to be the number of days to add
            # to the start of our period to get the entire month
            one_month = timedelta(
                days=monthrange(period_start.year, period_start.month)[1]
            )
                        
            # we want the first day of the next month
            period_end = period_start + one_month

        # okay we are going to calculate this users analytics
        # for this scope

        # 1. get all the links for this user in this scope
        if hasattr(self, 'user_'):
            links = self.user_.filter('creation_time >=', period_start)\
                        .filter('creation_time <', period_end)
        else:
            logging.info('user has no links, exciting')
            return # GTFO, user has no links
        
        # 2. okay, we are going to go through each link
        # and put them in a list for a particular campaign
        # then once we have a list of links for a")ampaign
        # we create an user_analytics from the links
        app_id = None
        app_links = []
        ua = None
        services = ['facebook', 'linkedin', 'twitter', 'email', 'total']
        for link in links:
            try:
                app = link.app_
            except Exception,e:
                logging.error('Error getting app for link: %s' % e, exc_info=True)
                continue

            if app.uuid != app_id:
                # new campaign, new useranalytics!
                ua = get_or_create_ua(
                    user = self,
                    app = app,
                    scope = scope,
                    period_start = period_start
                )
                
                stats = {}
                for service in services:
                    stats[service] = get_or_create_ss(ua, service)

                    # we get the reach for the service now too
                    # because we're awesome like that
                    stats[service].reach = self.get_reach(service)

                app_id = app.uuid

            # figure out which service we are using
            if link.tweet_id != '':
                service = 'twitter'
            elif link.facebook_share_id != '':
                service = 'facebook'
            elif link.linkedin_share_url != '':
                service = 'linkedin'
            elif link.email_sent == True:
                service = 'email'
            else:
                # couldn't find the service
                logging.error('error tracking user share that has no service')
                logging.error(link)
                continue # on to next link!
            
            # let's increment some counters! 
            # starting witht the shares!
            stats[service].shares += 1
            stats['total'].shares += 1
            
            # alright let's get some clicks
            clicks = link.count_clicks()
            stats[service].clicks += clicks 
            stats['total'].clicks += clicks

            # get the number of conversions...
            # step 4: ???
            # step 5: profit!
            conversions = 0
            profit = 0.0
            if hasattr(link, 'link_conversions'):
                for conversion in link.link_conversions:
                    try:
                        order_id = conversion.order
                        order = OrderShopify.all().filter('order_id =', order_id)
                        for o in order:
                            if hasattr(o, 'subtotal_price'):
                                profit += float(o.subtotal_price)
                    except:
                        # whatever
                        logging.error('exception getting conversions')
                    conversion += 1
            
            stats[service].profit += float(profit)
            stats['total'].profit += float(profit)

            stats[service].conversions += conversions
            stats['total'].conversions += conversions
            
            # let's save everything ...
            ua.put()
            stats[service].put()
            stats['total'].put()
        link_count = links.count()
        if link_count > 0:
            logging.warn('processed %d links' % link_count)
        else:
            logging.info('no links to process')   
        return
    
    def get_analytics_for_app(self, 
            app=None, scope=None, order='period_start'):
        """ returns all the UA for this user for a 
            specified app """
        ret = None
        if app != None:
            #ret = self.users_analytics.filter('campaign=', campaign)
            ret = self.users_analytics
            logging.info ('user has %d UA' % ret.count())
            
            ret = ret.filter('app_ =', app)
            logging.info ('%d ua total' % ret.count())

            if not scope == None:
                ret = ret.filter('scope =', scope)
                logging.info ('%d ua total' % ret.count())

            if not order == None:
                ret = ret.order(order)
                logging.info ('%d ua total' % ret.count())
            #logging.info ('user has %d UA for campaign %s' % (ret.count(), campaign))
            
            #ret = UserAnalytics.all()#.filter('user =', self).filter('campaign =',campaign)
            #logging.info ('%d ua total' % ret.count())
            
            #ret = ret.filter('user =', self)
            #logging.info ('%d ua for user %s' % (ret.count(), self))

            #ret = ret.filter('campaign =', campaign)
            #logging.info ('%d ua for campaign %s' % (ret.count(), campaign))
        return ret
    
    def update_linkedin_info(self, extra={}):
        """updates the user attributes based on linkedin dict"""
        def linkedin_location(user, json):
            return json['country']['code']
        
        def linkedin_interests(user, json):
            l = []
            for interest in json.split(','):
                l.append(interest.strip())
            return l
        
        def linkedin_im_accounts(user, json):
            l = []
            if 'values' not in json:
                return l
            for value in json['values']:
                l.append(
                    '%s,%s' % (
                        value['im-account-type'],
                        value['im-account-name']
                    )
                )
            return l
        
        def linkedin_urls(user, json):
            l = []
            if 'values' not in json:
                return l
            for value in json['values']:
                l.append(value['url'])
            return l
        
        def linkedin_getlist(a_dict, key):
            l = []
            if 'values' not in a_dict:
                return l
            for value in a_dict['values']:
                if key in value:
                    l.append(value[key])
            return l
        
        def linkedin_connections(user, connections):
            l = []
            if 'values' not in connections:
                return l
            linkedin_connected_users = []
            for connection in connections['values']:
                l.append(connection['id'])
                new_user = get_or_create_user_by_linkedin(
                    connection['id'],
                    request_handler = None,
                    token = None,
                    referrer = None,
                    would_be = True,
                    extra = connection
                )
                linkedin_connected_users.append(new_user.key())
            user.update(
                linkedin_connected_users=linkedin_connected_users
            )
            return l
        
        mappings = {
            'headline': 'linkedin_headline',
            'firstName': 'linkedin_first_name',
            'lastName': 'linkedin_last_name',
            'numConnections': 'linkedin_num_connections',
            'numConnectionsCapped': 'linkedin_num_connections_capped',
            'location': {
                'attr': 'linkedin_location_country_code',
                'call': linkedin_location
            },
            'pictureUrl': 'linkedin_picture_url',
            'industry': 'linkedin_industry',
            'imAccounts': {
                'attr': 'linkedin_im_accounts',
                'call': linkedin_im_accounts
            },
            'interests': {
                'attr': 'linkedin_interests',
                'call': linkedin_interests
            },
            'memberUrlResources': {
                'attr': 'linkedin_urls',
                'key': 'url',
                'call': linkedin_getlist
            }, 
            'twitterAccounts': {
                'attr': 'linkedin_twitter_accounts',
                'key': 'providerAccountId',
                'call': linkedin_getlist
            },
            'connections': {
                'attr': 'linkedin_connections',
                'call': linkedin_connections
            }
        }
        for key in extra:
            try:
                if key not in mappings:
                    continue
                elif type(mappings[key]) == type(str()):
                    setattr(self, mappings[key], extra[key])
                else:
                    attr = mappings[key]['attr']
                    if 'key' in mappings[key]:
                        # use the defined key to call getlist
                        value = mappings[key]['call'](extra[key], mappings[key]['key'])
                    else:
                        value = mappings[key]['call'](self, extra[key])
                    if type(value) == type(list()):
                        if hasattr(self, attr):
                            old = self.get_attr(attr)
                            value.extend(old)
                    if value != []:
                        setattr(self, attr, value)
            except Exception, e:
                exception_type, exception, tb = sys.exc_info()
                logging.error('error updating user with linkedin dict:\n%s\n%s\n%s\n\n%s' % (e, print_tb(tb), key, extra[key]))
        self.put()
        return True
    #
    # Social Networking Share Functionality
    # 
    
    def tweet(self, message, img=None):
        """Tweet on behalf of a user. returns tweet_id, html_response.
           invocation: tweet_id, resp = user.tweet(message)
                       . . . self response.out.write(resp)"""
        
        # prepare the signed message to be sent to twitter
        if img != None:
            """
            twitter_post_url = 'http://upload.twitter.com/1/statuses/update_with_media.json'
            body= urllib.urlencode( {"status": message.encode("UTF-8"),
                                     "media[]" : img
                                                     } )
            
            content_type = "multipart/form-data"
            """
            message = "%s %s" % (message, img)
        else:
            twitter_post_url = 'http://api.twitter.com/1/statuses/update.json'
            body= urllib.urlencode( {"status": message.encode("UTF-8")} )
            content_type = "application/x-www-form-urlencoded"

        token = oauth.Token(
            key=self.twitter_access_token.oauth_token,
            secret=self.twitter_access_token.oauth_token_secret
        )

        consumer = oauth.Consumer(TWITTER_KEY, TWITTER_SECRET)

        client = oauth.Client(consumer, token)
        
        twitter_post_url = 'http://api.twitter.com/1/statuses/update.json'
        
        logging.info("Tweeting at %s" % twitter_post_url )
        
        response, content = client.request(
            twitter_post_url, 
            "POST", 
            body= urllib.urlencode( {"status": message.encode("UTF-8")} ),
            headers={ "Content-type":"application/x-www-form-urlencoded" }
        ) 
        logging.info("%r %r" % ( response, content ))

        res = simplejson.loads( content )

        # update user with info from twitter
        if res.has_key('id_str'):
            self.update_twitter_info(twitter_handle=res['user']['screen_name'],
                    twitter_profile_pic=res['user']['profile_image_url_https'],
                    twitter_name=res['user']['name'],
                    twitter_followers_count=res['user']['followers_count'])
            resp = "<script type='text/javascript'>" +\
                      "window.opener.shareComplete(); window.close();</script>"
            return res['id_str'], resp
        else:
            resp = "<script type='text/javascript'>" +\
                "window.opener.alert('Tweeting not successful');</script>"
            return None, resp
    
    def linkedin_share(self, message):
        """shares on linkedin on behalf of the user
            returns share_location, html_response
            invocation: share_location, resp = user.linkedin_share(message) ..."""
        
        linkedin_share_url = 'http://api.linkedin.com/v1/people/~/shares?twitter-post=true'
        body = '{"comment": "%s","visibility": {"code": "anyone"}}' % message
        params = {
            "oauth_consumer_key": LINKEDIN_KEY,
            "oauth_nonce": oauth.generate_nonce(),
            "oauth_timestamp": int(time()),
            "oauth_token" : self.linkedin_access_token.oauth_token,
            "oauth_version": "1.0"
        }
        token = oauth.Token(
            key=self.linkedin_access_token.oauth_token,
            secret=self.linkedin_access_token.oauth_token_secret
        )
        consumer = oauth.Consumer(LINKEDIN_KEY, LINKEDIN_SECRET)
        #req = oauth.Request(method="POST", url=url, body=body, headers={'x-li-format':'json'}, parameters=params)
        #signature_method = oauth.SignatureMethod_HMAC_SHA1()
        #req.sign_request(signature_method, consumer, token)
        
        client = oauth.Client(consumer, token)
        response, content = client.request(
            linkedin_share_url, 
            "POST", 
            body=body, 
            headers={
                'x-li-format':'json',
                'Content-Type': 'application/json'
            }
        )
        
        #params = {
        #    "oauth_consumer_key": LINKEDIN_KEY,
        #    "oauth_nonce": generate_uuid(16),
        #    "oauth_signature_method": "HMAC-SHA1",
        #    "oauth_timestamp": str(int(time())),
        #    "oauth_token" : self.linkedin_access_token.oauth_token,
        #    "oauth_version": "1.0"
        #}
        #params_encoded = '&'.join(['%s=%s' % (k, v) for k, v in params])
        #key = '&'.join([LINKEDIN_SECRET, self.linkedin_access_token.oauth_token])
        #msg = "&".join(["POST", linkedin_share_url, params_encoded])
        #signature = hmac(key, msg, sha1).digest().encode('base64').strip()
        #params['oauth_signature'] = signature
        #response = urlfetch.fetch(
        #    linkedin_share_url,
        #    payload=xml,
        #    method=urlfetch.POST,
        #    headers = params
        #)
        if int(response.status) == 201:
            # good response, get the location
            html_response = """<script type='text/javascript'>
                        window.opener.shareComplete(); window.close();
                    </script>"""
            content = response['location']
        else:
            # bad response, pop up an error
            logging.error('Error doing linkedin_share, response %s: %s\n\n%s\n\n%s\n%s\n%s' % (
                response.status,
                response,
                content,
                body,
                self.linkedin_access_token.oauth_token,
                self.linkedin_access_token.oauth_token_secret
            ))
            html_response = """
                <script type='text/javascript'>
                    window.opener.alert('LinkedIn sharing not successful');
                </script>
            """
            content = None
        logging.info('li share: %s' % response)
        return content, html_response
    
    def facebook_share(self, msg, img='', name='', desc='', link=None):
        """Share 'message' on behalf of this user. returns share_id, html_response
           invoation: fb_share_id, res = self.facebook_share(msg)...
                        ... self.response.out.write(res) """
        
        logging.info("LINK %s" % link )
        facebook_share_url = "https://graph.facebook.com/%s/feed" % self.fb_identity
        if img != "":

            caption = link.app_.store_url
            try:
                #caption = unicode(caption, 'utf-8', errors='ignore')
                caption = caption.encode('utf-8', 'ignore')
            except:
                logging.warn('cant unicode caption', exc_info=True)
            try:
                caption = caption.encode('ascii', 'ignore') 
            except:
                logging.warn('cant encode caption')

            temp = desc if desc != "" else name
            if isinstance(temp, str):
                temp = unicode(temp, 'utf-8', errors='ignore')

            params = urllib.urlencode({
                'access_token': self.fb_access_token,
                'message': msg,
                'picture' : img,
                'link' : link.get_willt_url(),
                'description' : temp,
                'name' : name,
                'caption' : caption 
            })
        else:
            params = urllib.urlencode({
                'access_token': self.fb_access_token,
                'message': unicode(msg, errors='ignore')
            })

        fb_response, plugin_response, fb_share_id = None, None, None
        try:
            logging.info(facebook_share_url + params)
            fb_response = urlfetch.fetch(facebook_share_url, 
                                         params,
                                         method=urlfetch.POST,
                                         deadline=7)
        except urlfetch.DownloadError, e: 
            logging.error('error sending fb request: %s' % e)
            return None, 'fail'
            # No response from facebook
            
        if fb_response is not None:
            
            fb_results = simplejson.loads(fb_response.content)
            if fb_results.has_key('id'):
                fb_share_id, plugin_response = fb_results['id'], 'ok'
                taskqueue.add(
                    url = url('FetchFacebookData'),
                    params = {
                        'fb_id': self.fb_identity
                    }
                )
            else:
                fb_share_id, plugin_response = None, 'fail'
                logging.info(fb_results)
        else:
            # we are assuming a nil response means timeout and success
            fb_share_id, plugin_response = None, 'ok'
            
            
        return fb_share_id, plugin_response

    def facebook_action(self, action, obj, obj_link):
        """Does an ACTION on OBJECT on users timeline"""
            
        url = "https://graph.facebook.com/me/shopify_buttons:%s?" % action 
        params = urllib.urlencode({
            'access_token': self.fb_access_token,
            obj: obj_link
        })

        fb_response, plugin_response, fb_share_id = None, False, None
        try:
            logging.info(url + params)
            fb_response = urlfetch.fetch(
                url, 
                params,
                method=urlfetch.POST,
                deadline=7
            )
        except urlfetch.DownloadError, e: 
            logging.error('error sending fb request: %s' % e)
            plugin_response = False
        else:
            try:
                results_json = simplejson.loads(fb_response.content)
                fb_share_id = results_json['id']
                plugin_response = True
                    
                # let's pull this users info
                taskqueue.add(
                    url = '/fetchFB',
                    params = {
                        'fb_id': self.fb_identity
                    }
                )
            except Exception, e:
                fb_share_id = None
                plugin_response = False
                logging.error('Error posting action: %s' % fb_response)
            
        return fb_share_id, plugin_response 

# Gets by X
def get_user_by_uuid( uuid ):
    logging.info("Getting user by uuid " + str(uuid))
    user = User.all().filter('uuid =', uuid).get()
    return user

def get_user_by_twitter(t_handle):
    logging.info("Getting user by T: " + t_handle)
    user = User.all().filter('twitter_handle =', t_handle).get()
    if user != None:
        logging.info('Pulled user: %s %s %s %s' % (t_handle, user.get_attr('twitter_pic_url'), user.get_attr('twitter_name'), user.get_attr('twitter_followers_count')))
        
        # If we don't have Klout data, let's fetch it!
        if user.get_attr('kscore') == '1.0':
            # Query Klout API for data
            taskqueue.add( queue_name='socialAPI', 
                           url='/klout', 
                           name= 'klout%s%s' % (t_handle, generate_uuid( 10 )),
                           params={'twitter_handle' : t_handle} )
    return user

def get_user_by_linkedin(linkedin_id):
    logging.info("Getting user by LID: " + linkedin_id)
    user = User.all().filter('linkedin_id =', linkedin_id).get()
    if user != None:
        logging.info('Pulled user: %s' % linkedin_id)
    
    return user

def get_user_by_facebook(fb_id):
    logging.info("Getting user by FB: " + fb_id)
    user = User.all().filter('fb_identity =', fb_id).get()
    return user

def get_user_by_facebook_for_taskqueue(fb_id):
    """Returns a user that is safe for taskqueue writing"""
    logging.info("Getting user by FB for taskqueue: " + fb_id)
    user = User.all().filter('fb_identity =', fb_id).get()
    klass = user.__class__
    props = dict((k, v.__get(e, klass)) for k, v in klass.properties().iteritems())
    props.update(clone=True)
    newUser = klass(**props)
    newUser.save()
    return newUser

def get_user_by_email( email ):
    logging.info("Getting user by email: " + email)
    email_model = EmailModel.all().filter( 'address = ', email ).get()
    return email_model.user if email_model else None

# Create by X
def create_user_by_twitter(t_handle, referrer, ip=''):
    """Create a new User object with the given attributes"""
    # check to see if this t_handle has an oauth token
    OAuthToken = apps.oauth.models.get_oauth_by_twitter(t_handle)
    
    user = User(key_name=t_handle,
                uuid=generate_uuid(16),
                twitter_handle=t_handle,
                referrer=referrer,
                ip=ip)
    
    if OAuthToken:
        user.twitter_access_token=OAuthToken
    
    user.put()
    
    # Query the SocialGraphAPI
    taskqueue.add( queue_name='socialAPI', 
                   url='/socialGraphAPI', 
                   name= 'soc%s%s' % (t_handle, generate_uuid( 10 )),
                   params={'id' : 'http://www.twitter.com/%s' % t_handle, 'uuid' : user.uuid} )
    
    return user

def create_user_by_linkedin(linkedin_id, referrer, ip='', would_be=False):
    """Create a new User object with the given attributes"""
    # check to see if this t_handle has an oauth token
    OAuthToken = apps.oauth.models.get_oauth_by_linkedin(linkedin_id)
    
    user = User(
        key_name = linkedin_id,
        uuid = generate_uuid(16),
        linkedin_id = linkedin_id,
        referrer = referrer,
        ip = ip,
        would_be = would_be
    )
    
    if OAuthToken:
        user.linkedin_access_token=OAuthToken
    
    user.put()
    
    # Query the SocialGraphAPI
    taskqueue.add (
        queue_name='socialAPI', 
        url = '/socialGraphAPI', 
        name = 'soc%s%s' % (linkedin_id, generate_uuid(10)),
        params = {
            'id' : 'http://www.linkedin.com/profile/view?id=%s' % linkedin_id, 
            'uuid' : user.uuid
        }
    )
    
    return user

def create_user_by_facebook(fb_id, first_name, last_name, name, email, referrer, token, would_be, friends):
    """Create a new User object with the given attributes"""
    user = User(key_name=fb_id,
                uuid=generate_uuid(16), fb_identity=fb_id, 
                fb_first_name=first_name, fb_last_name=last_name, fb_name=name,
                referrer=referrer, fb_access_token=token,
                would_be=would_be)
    if friends:
        user.fb_friends = friends
    user.put()
    
    # Query the SocialGraphAPI
    taskqueue.add( queue_name='socialAPI', 
                   url='/socialGraphAPI', 
                   name= fb_id + generate_uuid( 10 ),
                   params={'id' : fb_id, 'uuid' : user.uuid} )
    
    return user

def create_user_by_email(email, referrer):
    """Create a new User object with the given attributes"""
    user = User(key_name=email, uuid=generate_uuid(16), 
                email=email, referrer=referrer)
    user.put()
    
    return user

def create_user(referrer):
    """Create a new User object with the given attributes"""
    uuid=generate_uuid(16)
    user = User(key_name=uuid, uuid=uuid, referrer=referrer)
    user.put()
    
    return user

# Get or Create by X
def get_or_create_user_by_twitter(t_handle, name='', followers=None, profile_pic='', referrer=None, request_handler=None, token=None):
    """Retrieve a user object if it is in the datastore, othereise create
      a new object"""
    
    # First try to find them by cookie
    user = get_user_by_cookie( request_handler )
    
    # Then, search by Twitter handle
    if user is None:
        user = get_user_by_twitter(t_handle)    
    
    # Otherwise, make a new one
    if user is None:
        logging.info("Creating user: " + t_handle)
        user = create_user_by_twitter(t_handle, referrer)
    
    # Update the info
    user.update(twitter_handle=t_handle, twitter_name=name, 
                twitter_follower_count=followers, 
                twitter_profile_pic=profile_pic, referrer=referrer,
                twitter_access_token=token)

    # Set a cookie to identify the user in the future
    set_user_cookie(request_handler, user.uuid)
    
    logging.info('get_or_create_user: %s %s %s %s' % (t_handle, user.get_attr('twitter_pic_url'), user.get_attr('twitter_name'), user.get_attr('twitter_followers_count')))
    return user

def get_or_create_user_by_linkedin(linkedin_id, request_handler=None, token=None, referrer=None, would_be=False, extra={}):
    """Retrieve a user object if it is in the datastore, othereise create
      a new object"""
    
    # First try to find them by cookie
    if request_handler != None:
        user = get_user_by_cookie(request_handler)
    else:
        user = None
       
    # Then, search by linkedin handle
    if user is None:
        user = get_user_by_linkedin(linkedin_id)
    
    # Otherwise, make a new one
    if user is None:
        logging.info("Creating user with linkedin_id: %s" % linkedin_id)
        user = create_user_by_linkedin(linkedin_id, referrer, would_be=would_be)
    
    # Update the info
    user.update(linkedin_id=linkedin_id, referrer=referrer, linkedin_access_token=token)

    # set the linkedin extra fields
    user.update_linkedin_info(extra)
    
    # Set a cookie to identify the user in the future
    if request_handler != None:
        set_user_cookie(request_handler, user.uuid)
     
    logging.info('get_or_create_user: %s' % linkedin_id)
    return user

def get_or_create_user_by_facebook(
        fb_id, first_name='', last_name='', name='', email='', referrer=None, 
        verified=None, gender='', token='', would_be=False, friends=[], 
        request_handler=None):
    """Retrieve a user object if it is in the datastore, otherwise create
      a new object"""
     
    # First try to find them by cookie if request handle present
    user = get_user_by_cookie(request_handler) if request_handler is not None\
        else None
    
    # Try looking by FB identity
    if user is None:
        user = get_user_by_facebook(fb_id)
    
    # Otherwise, make a new one
    if user is None:
        logging.info("Creating user: " + fb_id)
        user = create_user_by_facebook(fb_id, first_name, last_name, name, 
                                       email, referrer, token, would_be, friends)
        # check to see if this user was added by reading another user's social graph
        # if so, pull profile data
        if user.would_be:
            taskqueue.add(url = '/fetchFB', params = {'fb_id': user.fb_identity})
    
    # Update the user
    user.update(
        fb_identity=fb_id,
        fb_first_name=first_name, 
        fb_last_name=last_name,
        fb_name=name,
        fb_email=email,
        referrer=referrer,
        fb_gender=gender,
        fb_verified=verified,
        fb_access_token=token,
        fb_friends=friends
    )

    # Set a cookie to identify the user in the future
    if request_handler is not None:
        set_user_cookie( request_handler, user.uuid )
    
    return user

def get_or_create_user_by_email(email, referrer=None, request_handler=None):
    """Retrieve a user object if it is in the datastore, otherwise create
      a new object"""
    
    # First try to find them by cookie
    user = get_user_by_cookie( request_handler )
    
    # Then find via email
    if user is None:
        user = get_user_by_email(email)  
    
    # Otherwise, make a new one
    if user is None:
        logging.info("Creating user: " + email)
        user = create_user_by_email(email, referrer)
    
    # Update the user
    user.update( email=email, referrer=referrer )
    
    # Set a cookie to identify the user in the future
    set_user_cookie( request_handler, user.uuid )
    
    return user

def get_user_by_cookie(request_handler):
    """Read a user by cookie. Update IP address if present"""
    uuid = read_user_cookie( request_handler )
    if uuid:
        user = get_user_by_uuid(uuid)
        if user:
            ip = request_handler.request.remote_addr
            if hasattr(user, 'ips') and ip not in user.ips:
                user.ips.append(ip)
            else: 
                user.ips = [ip]
            user.save()
            return user
    return None

def get_or_create_user_by_cookie( request_handler, referrer=None ): 
    user= get_user_by_cookie( request_handler )
    if user is None:
        user = create_user( referrer )

    # Set a cookie to identify the user in the future
    set_user_cookie(request_handler, user.uuid)

    return user

# ------------------------------------------------------------------------------
# Relationship Class Definition ------------------------------------------------
# ------------------------------------------------------------------------------

# NOTE:
#
# This is a TENTATIVE model. It is not in use.
#
class Relationship(Model):
    """Model storing inter-user relationships data"""
    uuid      = db.StringProperty( indexed = True )
    created   = db.DateTimeProperty(auto_now_add=True)
    from_user = db.ReferenceProperty( db.Model, collection_name="from_relationships" )
    to_user   = db.ReferenceProperty( db.Model, default = None, collection_name="to_relationships" )
    type      = db.StringProperty( default = 'friend' )
    provider  = db.StringProperty( )

    def __init__(self, *args, **kwargs):
        self._memcache_key = kwargs['uuid'] if 'uuid' in kwargs else None 
        super(Relationship, self).__init__(*args, **kwargs)
    
    @staticmethod
    def _get_from_datastore( uuid ):
        """Datastore retrieval using memcache_key"""
        return db.Query(Relationship).filter('uuid =', uuid).get()

def create_relationship( from_u, to_u, provider = '' ):
    uuid = generate_uuid(16)
    
    r = Relationship( key_name  = uuid,
                      uuid      = uuid,
                      from_user = from_u,
                      to_user   = to_u,
                      provider  = provider )
    r.put()

    return r # return incase the caller wants it
