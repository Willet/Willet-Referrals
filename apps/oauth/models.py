import sys, logging, urllib, urllib2

from datetime import datetime, timedelta
from hashlib import sha1
from hmac import new as hmac
from os.path import dirname, join as join_path
from random import getrandbits
from time import time
from cgi import parse_qsl
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
from util import oauth2 as oauth

# ------------------------------------------------------------------------------
# CALLBACKS FOR OAUTH
# ------------------------------------------------------------------------------
def twitter_callback(client, message, willt_code):
    """callback for twitter"""
    # check to see if we have a user with this twitter handle
    user = models.user.get_or_create_user_by_twitter(t_handle=client.token.specifier,
                                                     token=client.token,
                                                     request_handler=client.handler)
    # tweet and save results to user's twitter profle
    tweet_id, html_response = user.tweet(message)
    # update link with tweet id
    link = get_link_by_willt_code(willt_code)
    if link:
        link.user = user
        link.campaign.increment_shares()
        if tweet_id is not None:
            link.tweet_id = tweet_id
        link.save()
    return html_response

def linkedin_callback(client, message, willt_code):
    """callback for linkedin"""
    # check to see if we have a user with this linkedin handle?
    
    if hasattr(client, 'linkedin_extra'):
        linkedin_extra = client.linkedin_extra
    else:
        linkedin_extra = {}
    
    user = models.user.get_or_create_user_by_linkedin(
        linkedin_id=client.token.specifier,
        token=client.token,
        request_handler=client.handler,
        extra=linkedin_extra
    )
    
    # share and save results to user's profle
    linkedin_share_url, html_response = user.linkedin_share(message)
    # update link with linkedin_share_url
    link = get_link_by_willt_code(willt_code)
    if link:
        link.user = user
        link.campaign.increment_shares()
        if linkedin_share_url is not None:
            link.linkedin_share_url = linkedin_share_url
        link.save()
    return html_response

def twitter_specifier_handler(client):
    return client.get('/account/verify_credentials')['screen_name']

def linkedin_specifier_handler(client):
    fields = ','.join([
        'id',
        'first-name',
        'last-name',
        'industry',
        'num-connections',
        'num-connections-capped',
        'connections',
        'interests',
        'im-accounts',
        'member-url-resources',
        'picture-url',
        'twitter-accounts',
        'location:(country:(code))',
    ])
    response = client.get('/v1/people/~:(%s)' % fields)
    
    if 'id' in response:
        client.linkedin_extra = response
        return response['id']
    # else
    logging.error('linkedin api call failed, returned: %s' % response)
    return None


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
        
        'callback': twitter_callback,
        'specifier_handler': twitter_specifier_handler
    }, 
    'linkedin': {
        'consumer_key': LINKEDIN_KEY,
        'consumer_secret': LINKEDIN_SECRET,
        
        'request_token_url': 'https://api.linkedin.com/uas/oauth/requestToken',
        'access_token_url': 'https://api.linkedin.com/uas/oauth/accessToken',
        'user_auth_url': 'https://www.linkedin.com/uas/oauth/authenticate',
        
        'default_api_prefix': 'https://api.linkedin.com',
        'default_api_suffix': '',
        
        'callback': linkedin_callback,
        'specifier_handler': linkedin_specifier_handler
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
    return urlquote(str(text), safe='-._~')


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

def get_oauth_by_linkedin(linkedin_id):
    """docstring for get_oauth_by_linkedin"""
    access_token = OAuthAccessToken.all().filter(
        'service = ', 'linkedin').filter(
        'specifier = ', linkedin_id).get()
    return access_token


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
        self.consumer = oauth.Consumer(self.service_info['consumer_key'], self.service_info['consumer_secret'])
    
    # public methods
    
    def get(self, api_method, http_method='GET', headers={'x-li-format':'json'}, expected_status=(200,), return_json=True, **extra_params):
        
        if not (api_method.startswith('http://') or api_method.startswith('https://')):
            api_method = '%s%s%s' % (
                self.service_info['default_api_prefix'],
                api_method,
                self.service_info['default_api_suffix']
            )
        
        if self.token is None:
            logging.info('No access token, getting by key_name from cookie')
            self.token = OAuthAccessToken.get_by_key_name(self.get_cookie())
        
        # Create our client and token
        token = oauth.Token(
            key=self.token.oauth_token,
            secret=self.token.oauth_token_secret
        )
        client = oauth.Client(self.consumer, token)
        
        # The OAuth Client request works just like httplib2 for the most part.
        response, content = client.request(api_method, "GET", headers=headers)
        
        #body = self.get_signed_url(
        #    api_method, 
        #    self.token, 
        #    http_method, 
        #    **extra_params
        #)
        #fetch = urlfetch(body)
        
        if int(response['status']) not in expected_status:
            raise ValueError(
                "Error calling... Got return status: %i [%r]\n\n\n<====>\napi_method=%s\nself.token.oauth_token=%s\nself.token.oauth_token_secret=%s\n\nbody=\n%s" % (
                    response['status'], 
                    content,
                    api_method,
                    self.token.oauth_token,
                    self.token.oauth_token_secret,
                    body
                )
            )
        if return_json:
            return decode_json(content)
        return content
    
    def post(self, api_method, http_method='POST', headers={'x-li-format':'json'}, body='', expected_status=(200,), return_json=True, **extra_params):
        
        if not (api_method.startswith('http://') or api_method.startswith('https://')):
            api_method = '%s%s%s' % (
                self.service_info['default_api_prefix'],
                api_method,
                self.service_info['default_api_suffix']
            )
        
        if self.token is None:
            self.token = OAuthAccessToken.get_by_key_name(self.get_cookie())
        
        # Create our client and token
        token = oauth.Token(
            key=self.token.oauth_token,
            secret=self.token.oauth_token_secret
        )
        
        client = oauth.Client(self.consumer, token)
        
        # The OAuth Client request works just like httplib2 for the most part.
        response, content = client.request(api_method, "POST", body=body, headers=headers)
        
        #fetch = urlfetch(
        #    url=api_method, 
        #    payload=self.get_signed_body(
        #        api_method, 
        #        self.token, 
        #        http_method, 
        #        **extra_params
        #    ), method=http_method,
        #    headers = headers
        #)
        
        if int(response['status']) not in expected_status:
            raise ValueError(
                "Error calling... Got return status: %i [%r]\n\n\n<====>\napi_method=%s\nself.token.oauth_token=%s\nself.token.oauth_token_secret=%s\n\nbody=\n%s" % (
                    response['status'], 
                    content,
                    api_method,
                    self.token.oauth_token,
                    self.token.oauth_token_secret,
                    body
                )
            )
        if return_json:
            return decode_json(content)
        return content
    
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
    
    def get_request_token(self, msg='', wcode='', expected_status=(200,)):
        
        #consumer = oauth.Consumer(self.service_info['consumer_key'], self.service_info['consumer_secret'])
        client = oauth.Client(self.consumer)
        
        response, content = client.request(self.service_info['request_token_url'], 'GET')
        if int(response['status']) not in expected_status:
            raise Exception('Invalid response %s' % response['status'])
        
        request_token = dict(parse_qsl(content))
        
        token = OAuthRequestToken(
            message=msg,
            willt_code=wcode,
            service=self.service,
            oauth_token = request_token['oauth_token'],
            oauth_token_secret = request_token['oauth_token_secret']
        )
        
        # replaced with python-oauth2 code above
        #
        #token_info = self.get_data_from_signed_url(
        #    self.service_info['request_token_url'], **self.request_params
        #)
        #
        #token = OAuthRequestToken(
        #    message=msg,
        #    willt_code=wcode,
        #    service=self.service,
        #    **dict(token.split('=') for token in token_info.split('&'))
        #)
        
        token.put()
        
        if self.oauth_callback:
            oauth_callback = {'oauth_callback': self.oauth_callback}
        elif 'oauth_callback' in self.service_info:
            oauth_callback = {'oauth_callback': self.service_info['oauth_callback']}
        else:
            oauth_callback = {}
        
        #redirect_url = self.get_signed_url(
        #    self.service_info['user_auth_url'],
        #    token,
        #    **oauth_callback
        #)
        
        redirect_url = '%s?oauth_token=%s' % (
            self.service_info['user_auth_url'],
            request_token['oauth_token']
        )
        
        logging.info('redirecting to: %s' % redirect_url)
        self.handler.redirect(redirect_url)
    
    def callback(self, return_to='/account'):
        
        oauth_token = self.handler.request.get("oauth_token")
        oauth_verifier = self.handler.request.get('oauth_verifier')
        
        message = ''
        willt_code = ''
        
        if not oauth_token:
            return self.get_request_token()
        
        oauth_token = OAuthRequestToken.all().filter(
            'oauth_token =', oauth_token).filter(
            'service =', self.service).fetch(1)[0]
        message = oauth_token.message
        willt_code = oauth_token.willt_code
        
        logging.info('set oauth_verifier=%s' % oauth_verifier)
        
        request_token = oauth.Token(
            oauth_token.oauth_token, 
            oauth_token.oauth_token_secret
        )
        
        request_token.set_verifier(oauth_verifier)
        client = oauth.Client(self.consumer, request_token)
        response, content = client.request(
            self.service_info['access_token_url'],
            "POST"
        )
        
        access_token = dict(parse_qsl(content))
        
        key_name = create_uuid()
        
        self.token = OAuthAccessToken(
            key_name=key_name,
            service=self.service,
            oauth_token = access_token['oauth_token'],
            oauth_token_secret = access_token['oauth_token_secret']
        )
        
        #token_info = self.get_data_from_signed_url(
        #    self.service_info['access_token_url'],
        #    oauth_token,
        #    'GET',
        #    oauth_verifier = oauth_verifier
        #)
        #logging.info('got token_info: %s' % token_info)
        #key_name = create_uuid()
        #
        #self.token = OAuthAccessToken(
        #    key_name=key_name,
        #    service=self.service,
        #    **dict(token.split('=') for token in token_info.split('&'))
        #)
        #
        
        if 'specifier_handler' in self.service_info:
            specifier = self.token.specifier = self.service_info['specifier_handler'](self)
            old = OAuthAccessToken.all().filter(
                'specifier =', specifier).filter(
                'service =', self.service)
            db.delete(old)
        
        self.token.put()
        
        if 'callback' in self.service_info:
            html_response = self.service_info['callback'](self, message, willt_code)
        else:
            html_response = 'poop'
        
        self.set_cookie(key_name)
        #self.handler.redirect(return_to)
        self.handler.response.headers.add_header("Content-type", 'text/javascript')
        self.handler.response.out.write(html_response)
    
    def cleanup(self):
        query = OAuthRequestToken.all().filter(
            'created <', datetime.now() - EXPIRATION_WINDOW
            )
        count = query.count(CLEANUP_BATCH_SIZE)
        db.delete(query.fetch(CLEANUP_BATCH_SIZE))
        return "Cleaned %i entries" % count
    
    
    # request marshalling
    
    def get_data_from_signed_url(self, __url, __token=None, __meth='GET', **extra_params):
        logging.info(
            """
                get_data_from_signed_url
                __url = %s
                __token = %s
                __meth = %s
                extra_params = %s
            """ % (
                __url, 
                __token, 
                __meth, 
                extra_params
            )
        )
        return urlfetch(
            self.get_signed_url(
                __url,
                __token,
                __meth,
                **extra_params
            )).content
    
    def get_signed_url(self, __url, __token=None, __meth='GET',**extra_params):
        logging.info(
            """
                get_signed_url
                __url = %s
                __token = %s
                __meth = %s
                extra_params = %s
            """ % (
                __url, 
                __token, 
                __meth, 
                extra_params
            )
        )
        return '%s?%s' % (
            __url, 
            self.get_signed_body(
                __url, 
                __token, 
                __meth, 
                **extra_params
            )
        )
    
    def get_signed_body(self, __url, __token=None, __meth='GET',**extra_params):
        logging.info(
            """
                get_signed_body
                    __url = %s
                    __token = %s
                    __meth = %s
                    extra_params = %s
            """ % (
                __url, 
                __token, 
                __meth, 
                extra_params
            )
        )
        service_info = self.service_info
        nonce = getrandbits(64)
        timestamp = int(time())
        kwargs = {
            'oauth_consumer_key': service_info['consumer_key'],
            'oauth_signature_method': 'HMAC-SHA1',
            'oauth_version': '1.0',
            'oauth_timestamp': timestamp,
            'oauth_nonce': nonce,
        }
        
        kwargs.update(extra_params)
        
        if self.service_key is None:
            self.service_key = get_service_key(self.service)
        
        if __token is not None:
            kwargs['oauth_token'] = __token.oauth_token
            key = self.service_key + encode(__token.oauth_token_secret)
            logging.info(
                """
                self.service_key=%s
                __token.oauth_token_secret=%s
                encode(__token.oauth_token_secret)=%s
                key=%s
                """ % (
                    self.service_key,
                    __token.oauth_token_secret,
                    encode(__token.oauth_token_secret),
                    key
                )
            )
        else:
            key = self.service_key
            
        keys_and_values = [(encode(k), encode(v)) for k,v in kwargs.items()]
        keys_and_values.sort()
        query_string = '&'.join(['%s=%s' % (k, v) for k, v in keys_and_values])
    
        #query_string = '&'.join(
        #    '%s=%s' % (
        #        encode(k), 
        #        encode(kwargs[k])
        #    ) for k in sorted(kwargs)
        #)
        
        message_uncoded ='&'.join([ 
            __meth.upper(), 
            __url, 
            query_string
        ])
        message = '&'.join(map(encode, [ __meth.upper(), __url, query_string]))
        
        kwargs['oauth_signature'] = hmac(
            key,
            message,
            sha1
        ).digest().encode('base64')[:-1]
        
        if __token is not None:
            logging.info(
                """
                signature stuff
                    api_key         = %s
                    secret_key      = %s
                    token           = %s
                    token_secret    = %s
                    http verb       = %s
                    url             = %s
                
                    nonce           = %s
                    timestamp       = %s
                    oauth version   = %s
                    
                    query string =
                    %s
                    
                    message_before =
                    %s
                    
                    message_after =
                    %s
                
                    signature =
                    %s
                """ % (
                    LINKEDIN_KEY,
                    LINKEDIN_SECRET,
                    __token.oauth_token,
                    __token.oauth_token_secret,
                    __meth,
                    __url,
                    nonce,
                    timestamp,
                    '1.0',
                    query_string,
                    message_uncoded,
                    message,
                    kwargs['oauth_signature']
                )
            )
        
        return urlencode(kwargs)
    
    def get_signed_authorization(self, __url, __token=None, __meth='GET',**extra_params):
        pass
    
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
    

