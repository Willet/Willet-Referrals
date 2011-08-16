import sys, logging, urllib, urllib2

from datetime import datetime, timedelta
from hashlib import sha1
from hmac import new as hmac
from os.path import dirname, join as join_path
from random import getrandbits
from time import time
from urllib import urlencode, quote as urlquote
from uuid import uuid4
from wsgiref.handlers import CGIHandler

sys.path.insert(0, join_path(dirname(__file__), 'lib')) # extend sys.path

from django.utils.simplejson import loads as decode_json

from google.appengine.api.urlfetch import fetch as urlfetch, GET, POST
from google.appengine.ext import db
from google.appengine.ext.webapp import RequestHandler, WSGIApplication

import models.user
from models.link import get_link_by_willt_code
from util.consts import *
from util.helpers import generate_uuid

# ------------------------------------------------------------------------------
# configuration -- SET THESE TO SUIT YOUR APP!!
# ------------------------------------------------------------------------------

OAUTH_APP_SETTINGS = {
    'twitter': {
        
        'consumer_key': TWITTER_KEY,
        'consumer_secret': TWITTER_SECRET,
        
        'request_token_url': 'https://twitter.com/oauth/request_token',
        'access_token_url': 'https://twitter.com/oauth/access_token',
        'user_auth_url': 'http://twitter.com/oauth/authorize',
        
        'default_api_prefix': 'http://twitter.com',
        'default_api_suffix': '.json',
        
    }, 
    'linkedin': {
        'consumer_key': LINKEDIN_KEY,
        'consumer_secret': LINKEDIN_SECRET,
        
        'request_token_url': 'https://api.linkedin.com/uas/oauth/requestToken',
        'access_token_url': 'https://api.linkedin.com/uas/oauth/accessToken',
        'user_auth_url': 'https://www.linkedin.com/uas/oauth/authenticate',
        
        'default_api_prefix': 'https://api.linkedin.com',
        'default_api_suffix': '.json',
        
        'oauth_callback': '%s/oauth/linkedin/callback' % URL
    }
}

CLEANUP_BATCH_SIZE = 100
EXPIRATION_WINDOW = timedelta(seconds=60*60*1) # 1 hour

try:
    from config import OAUTH_APP_SETTINGS
except:
    pass

STATIC_OAUTH_TIMESTAMP = 12345 # a workaround for clock skew/network lag

# ------------------------------------------------------------------------------
# utility functions
# ------------------------------------------------------------------------------

def get_service_key(service, cache={}):
    if service in cache: return cache[service]
    return cache.setdefault(
        service, "%s&" % encode(OAUTH_APP_SETTINGS[service]['consumer_secret'])
        )

def create_uuid():
    return 'id-%s' % uuid4()

def encode(text):
    return urlquote(str(text), '')

def twitter_specifier_handler(client):
    return client.get('/account/verify_credentials')['screen_name']

OAUTH_APP_SETTINGS['twitter']['specifier_handler'] = twitter_specifier_handler

# ------------------------------------------------------------------------------
# db entities
# ------------------------------------------------------------------------------

class OAuthRequestToken(db.Model):
    """OAuth Request Token."""
    
    service = db.StringProperty()
    oauth_token = db.StringProperty()
    oauth_token_secret = db.StringProperty()
    created = db.DateTimeProperty(auto_now_add=True)
    message = db.StringProperty(indexed=False)
    willt_code = db.StringProperty()

class OAuthAccessToken(db.Model):
    """OAuth Access Token."""
    
    service = db.StringProperty()
    specifier = db.StringProperty(indexed=True)
    oauth_token = db.StringProperty()
    oauth_token_secret = db.StringProperty()
    created = db.DateTimeProperty(auto_now_add=True)


def get_oauth_by_twitter(t_handle):
    return OAuthAccessToken.all().filter('specifier =', t_handle).get()


# ------------------------------------------------------------------------------
# oauth client
# ------------------------------------------------------------------------------

class OAuthClient(object):
    
    __public__ = ('callback', 'cleanup', 'login', 'logout')
    
    def __init__(self, service, handler, oauth_callback=None, **request_params):
        self.service = service
        self.service_info = OAUTH_APP_SETTINGS[service]
        self.service_key = None
        self.handler = handler
        self.request_params = request_params
        self.oauth_callback = oauth_callback
        self.token = None
    
    # public methods
    
    def get(self, api_method, http_method='GET', expected_status=(200,), **extra_params):
        
        if not (api_method.startswith('http://') or api_method.startswith('https://')):
            api_method = '%s%s%s' % (
                self.service_info['default_api_prefix'], api_method,
                self.service_info['default_api_suffix']
                )
        
        if self.token is None:
            self.token = OAuthAccessToken.get_by_key_name(self.get_cookie())
        
        fetch = urlfetch(self.get_signed_url(
            api_method, self.token, http_method, **extra_params
            ))
        
        if fetch.status_code not in expected_status:
            raise ValueError(
                "Error calling... Got return status: %i [%r]" %
                (fetch.status_code, fetch.content)
                )
        
        return decode_json(fetch.content)
    
    def post(self, api_method, http_method='POST', expected_status=(200,), return_json=True, **extra_params):
        
        if not (api_method.startswith('http://') or api_method.startswith('https://')):
            api_method = '%s%s%s' % (
                self.service_info['default_api_prefix'],
                api_method,
                self.service_info['default_api_suffix']
            )
        
        if self.token is None:
            self.token = OAuthAccessToken.get_by_key_name(self.get_cookie())
        
        fetch = urlfetch(
            url=api_method, 
            payload=self.get_signed_body(
                api_method, 
                self.token, 
                http_method, 
                **extra_params
            ), method=http_method
        )
        
        if fetch.status_code not in expected_status:
            raise ValueError(
                "Error calling... Got return status: %i [%r]" % (
                    fetch.status_code, 
                    fetch.content
                )
            )
        if return_json:            
            return decode_json(fetch.content)
        return fetch # else
    
    def login(self, message, willt_code):
        
        proxy_id = self.get_cookie()
        
        if proxy_id:
            #return "FOO%rFF" % proxy_id
            self.expire_cookie()
            
        logging.info("We're sending you to get your request token with your message: " + message)
        return self.get_request_token(message, willt_code)
    
    def logout(self, return_to='/'):
        self.expire_cookie()
        self.handler.redirect(self.handler.request.get("return_to", return_to))
    
    # oauth workflow
    
    def get_request_token(self, msg='', wcode=''):
        
        token_info = self.get_data_from_signed_url(
            self.service_info['request_token_url'], **self.request_params
        )
        
        token = OAuthRequestToken(
            message=msg,
            willt_code=wcode,
            service=self.service,
            **dict(token.split('=') for token in token_info.split('&'))
        )
        
        token.put()
        
        if self.oauth_callback:
            oauth_callback = {'oauth_callback': self.oauth_callback}
        elif 'oauth_callback' in self.service_info:
            oauth_callback = {'oauth_callback': self.service_info['oauth_callback']}
        else:
            oauth_callback = {}
        
        redirect_url = self.get_signed_url(
            self.service_info['user_auth_url'],
            token,
            **oauth_callback
        )
        logging.info('redirecting to: %s' % redirect_url)
        self.handler.redirect(redirect_url)
    
    def callback(self, return_to='/account'):
        
        oauth_token = self.handler.request.get("oauth_token")
        message = ''
        willt_code = ''
        
        if not oauth_token:
            return get_request_token()
        
        oauth_token = OAuthRequestToken.all().filter(
            'oauth_token =', oauth_token).filter(
            'service =', self.service).fetch(1)[0]
        message = oauth_token.message
        willt_code = oauth_token.willt_code
        
        token_info = self.get_data_from_signed_url(
            self.service_info['access_token_url'], oauth_token
        )
        
        key_name = create_uuid()
        
        self.token = OAuthAccessToken(
            key_name=key_name, service=self.service,
            **dict(token.split('=') for token in token_info.split('&'))
        )
        
        if 'specifier_handler' in self.service_info:
            specifier = self.token.specifier = self.service_info['specifier_handler'](self)
            old = OAuthAccessToken.all().filter(
                'specifier =', specifier).filter(
                'service =', self.service)
            db.delete(old)
        
        self.token.put()
        # check to see if we have a user with this twitter handle
        user = models.user.get_or_create_user_by_twitter(t_handle=self.token.specifier,
                                                         token=self.token,
                                                         request_handler=self.handler)
        # tweet and save results to user's twitter profle
        tweet_id, res = user.tweet(message)
        # update link with tweet id
        link = get_link_by_willt_code(willt_code)
        if link:
            link.user = user
            if tweet_id is not None:
                link.tweet_id = tweet_id
            link.save()
        self.set_cookie(key_name)
        #self.handler.redirect(return_to)
        self.handler.response.headers.add_header("Content-type", 'text/javascript')
        self.handler.response.out.write(res)
    
    def cleanup(self):
        query = OAuthRequestToken.all().filter(
            'created <', datetime.now() - EXPIRATION_WINDOW
            )
        count = query.count(CLEANUP_BATCH_SIZE)
        db.delete(query.fetch(CLEANUP_BATCH_SIZE))
        return "Cleaned %i entries" % count
    
    
    # request marshalling
    
    def get_data_from_signed_url(self, __url, __token=None, __meth='GET', **extra_params):
        return urlfetch(self.get_signed_url(
            __url, __token, __meth, **extra_params
            )).content
    
    def get_signed_url(self, __url, __token=None, __meth='GET',**extra_params):
        return '%s?%s'%(__url, self.get_signed_body(__url, __token, __meth, **extra_params))
    
    def get_signed_body(self, __url, __token=None, __meth='GET',**extra_params):
        
        service_info = self.service_info
        
        kwargs = {
            'oauth_consumer_key': service_info['consumer_key'],
            'oauth_signature_method': 'HMAC-SHA1',
            'oauth_version': '1.0',
            'oauth_timestamp': int(time()),
            'oauth_nonce': getrandbits(64),
        }
            
        kwargs.update(extra_params)
        
        if self.service_key is None:
            self.service_key = get_service_key(self.service)
        
        if __token is not None:
            kwargs['oauth_token'] = __token.oauth_token
            key = self.service_key + encode(__token.oauth_token_secret)
        else:
            key = self.service_key
        
        message = '&'.join(map(encode, [
            __meth.upper(), __url, '&'.join(
                '%s=%s' % (encode(k), encode(kwargs[k])) for k in sorted(kwargs)
                )
            ]))
        
        kwargs['oauth_signature'] = hmac(
            key, message, sha1
            ).digest().encode('base64')[:-1]
        
        return urlencode(kwargs)
    
    # who stole the cookie from the cookie jar?
    
    def get_cookie(self):
        return self.handler.request.cookies.get(
            'oauth.%s' % self.service, ''
            )
    
    def set_cookie(self, value, path='/'):
        self.handler.response.headers.add_header(
            'Set-Cookie', 
            'oauth.%s=%s; path=%s; expires="Fri, 31-Dec-2021 23:59:59 GMT"' % (
                self.service,
                value,
                path
            )
        )
    
    def expire_cookie(self, path='/'):
        self.handler.response.headers.add_header(
            'Set-Cookie', 
            '%s=; path=%s; expires="Fri, 31-Dec-1999 23:59:59 GMT"' %
            ('oauth.%s' % self.service, path)
            )
    

