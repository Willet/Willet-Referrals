#!/usr/bin/env python
# Data models for our Users
# our Users are our client's clients
import logging
import sys

from django.utils import simplejson

from datetime import datetime
from decimal  import *
from time import time
from hmac import new as hmac
from hashlib import sha1
from traceback import print_tb

from google.appengine.api import memcache
from google.appengine.api import urlfetch
from google.appengine.api import taskqueue
from google.appengine.ext import db
from models.model         import Model
from models.oauth         import OAuthClient
from util.emails          import Email
from util.helpers         import *
from util import oauth2 as oauth

import models.oauth

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
            elif kwargs[k] != '' and kwargs[k] != None:
                setattr( self, k, kwargs[k] )
        self.put()
        """
        if 'twitter_handle' in kwargs and kwargs['twitter_handle'] != '':
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
    
    def get_attr( self, attr_name ):
        if attr_name == 'email':
            return self.emails[0].address if self.emails.count() > 0 else ''
        
        if hasattr( self, attr_name ):
            return getattr( self, attr_name )
    
    def update_twitter_info(self, **kwargs):
        fields = ['twitter_handle', 'twitter_profile_pic', 'twitter_followers_count', 'twitter_name', 'twitter_access_token']
        insertion = {}
        for k in kwargs:
            if k in fields:
                insertion[k] = kwargs[k]
        self.update(**insertion)
    
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
    
    def tweet(self, message):
        """Tweet on behalf of a user. returns tweet_id, html_response.
           invocation: tweet_id, resp = user.tweet(message)
                       . . . self response.out.write(resp)"""
        
        # prepare the signed message to be sent to twitter
        twitter_post_url = 'http://api.twitter.com/1/statuses/update.json'
        params = { "oauth_consumer_key": TWITTER_KEY,
            "oauth_nonce": generate_uuid(16),
            "oauth_signature_method": "HMAC-SHA1",
            "oauth_timestamp": str(int(time())),
            "oauth_token": self.twitter_access_token.oauth_token,
            "oauth_version": "1.0"
        }
        status = {"status": message.encode("UTF-8")}
        params.update(status)
        key = "&".join([TWITTER_SECRET, self.twitter_access_token.oauth_token_secret])
        msg = "&".join(["POST", urllib.quote(twitter_post_url, ""),
                        urllib.quote("&".join([k+"="+urllib.quote(params[k],"-._~")\
                            for k in sorted(params)]),
                                     "-._~")])
        signature = hmac(key, msg, sha1).digest().encode("base64").strip()
        params["oauth_signature"] = signature
        req = urllib2.Request(twitter_post_url,
                              headers={"Authorization":"OAuth",
                                       "Content-type":"application/x-www-form-urlencoded"})
        req.add_data("&".join([k+"="+urllib.quote(params[k], "-._~") for k in params]))
        # make POST to twitter and parse response
        res = simplejson.loads(urllib2.urlopen(req).read())
        # TODO: handle failure response from twitter more gracefully
        
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
    
    def facebook_share(self, msg):
        """Share 'message' on behalf of this user. returns share_id, html_response
           invoation: fb_share_id, res = self.facebook_share(msg)...
                        ... self.response.out.write(res) """
        
        facebook_share_url = "https://graph.facebook.com/%s/feed"%self.fb_identity
        params = urllib.urlencode({'access_token': self.fb_access_token,
                                   'message': msg })
        fb_response, plugin_response, fb_share_id = None, None, None
        try:
            logging.info(facebook_share_url + params)
            fb_response = urlfetch.fetch(facebook_share_url, 
                                         params,
                                         method=urlfetch.POST,
                                         deadline=7)
        except urlfetch.DownloadError, e: 
            logging.info(e)
            return
            # No response from facebook
            
        if fb_response is not None:
            
            fb_results = simplejson.loads(fb_response.content)
            if fb_results.has_key('id'):
                fb_share_id, plugin_response = fb_results['id'], 'ok'
                taskqueue.add(url = '/fetchFB',
                              params = {'fb_id': self.fb_identity})
            else:
                fb_share_id, plugin_response = None, 'fail'
                logging.info(fb_results)
        else:
            # we are assuming a nil response means timeout and success
            fb_share_id, plugin_response = None, 'ok'
            
            
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

def get_user_by_email( email ):
    logging.info("Getting user by email: " + email)
    email_model = EmailModel.all().filter( 'address = ', email ).get()
    return email_model.user if email_model else None

# Create by X
def create_user_by_twitter(t_handle, referrer, ip=''):
    """Create a new User object with the given attributes"""
    # check to see if this t_handle has an oauth token
    OAuthToken = models.oauth.get_oauth_by_twitter(t_handle)
    
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
    OAuthToken = models.oauth.get_oauth_by_linkedin(linkedin_id)
    
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

# Get or Create by X
def get_or_create_user_by_twitter(t_handle, name='', followers=None, profile_pic='', referrer=None, request_handler=None, token=None):
    """Retrieve a user object if it is in the datastore, othereise create
      a new object"""
    
    # First try to find them by cookie
    user = get_user_by_cookie( request_handler )
    # Update the info
    if user:
        user.update(twitter_handle=t_handle, twitter_name=name, 
                    twitter_follower_count=followers, 
                    twitter_profile_pic=profile_pic, referrer=referrer,
                    twitter_access_token=token)
    
    # Then, search by Twitter handle
    if user is None:
        user = get_user_by_twitter(t_handle)    
    
    # Otherwise, make a new one
    if user is None:
        logging.info("Creating user: " + t_handle)
        user = create_user_by_twitter(t_handle, referrer)
    
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
    
    # Update the info
    if user:
        user.update(
            linkedin_id = linkedin_id,
            referrer = referrer,
            linkedin_access_token = token
        )
    
    # Then, search by linkedin handle
    if user is None:
        user = get_user_by_linkedin(linkedin_id)
    
    # Otherwise, make a new one
    if user is None:
        logging.info("Creating user with linkedin_id: %s" % linkedin_id)
        user = create_user_by_linkedin(linkedin_id, referrer, would_be=would_be)
    
    # Set a cookie to identify the user in the future
    if request_handler != None:
        set_user_cookie(request_handler, user.uuid)
    
    # set the linkedin extra fields
    user.update_linkedin_info(extra)
    
    logging.info('get_or_create_user: %s' % linkedin_id)
    return user

def get_or_create_user_by_facebook(fb_id, first_name='', last_name='', name='', email='', referrer=None, verified=None, gender='', token='', would_be=False, friends=[], request_handler=None):
    """Retrieve a user object if it is in the datastore, otherwise create
      a new object"""
     
    # First try to find them by cookie if request handle present
    user = get_user_by_cookie(request_handler) if request_handler is not None\
        else None
    if user:
        user.update( fb_identity=fb_id, fb_first_name=first_name, 
                     fb_last_name=last_name, fb_name=name, fb_email=email,
                     referrer=referrer, fb_gender=gender, fb_verified=verified,
                     fb_access=token, fb_friends=friends )
    
    # Try looking by FB identity
    if user is None:
        user = get_user_by_facebook(fb_id)
        if email != '':    
            create_email_model( self, email )
    
    # Otherwise, make a new one
    if user is None:
        logging.info("Creating user: " + fb_id)
        user = create_user_by_facebook(fb_id, first_name, last_name, name, 
                                       email, referrer, token, would_be, friends)
        # check to see if this user was added by reading another user's social graph
        # if so, pull profile data
        if user.would_be:
            taskqueue.add(url = '/fetchFB',
                              params = {'fb_id': user.fb_identity})
    
    # Set a cookie to identify the user in the future
    if request_handler is not None:
        set_user_cookie( request_handler, user.uuid )
    
    return user

def get_or_create_user_by_email(email, referrer=None, request_handler=None):
    """Retrieve a user object if it is in the datastore, otherwise create
      a new object"""
    
    # First try to find them by cookie
    user = get_user_by_cookie( request_handler )
    if user:
        user.update( email=email, referrer=referrer )
    
    # Then find via email
    if user is None:
        user = get_user_by_email(email)  
    
    # Otherwise, make a new one
    if user is None:
        logging.info("Creating user: " + email)
        user = create_user_by_email(email, referrer)
    
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

