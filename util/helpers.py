#!/usr/bin/env python

import cgi, hashlib, re, os, logging, urllib, urllib2, uuid, Cookie

from util.consts  import *
from util.cookies import LilCookies

def isGoodURL(url):
    if len(url) < 11:
        return False

    url = str(url)
    if not url.startswith(('http://', 'https://')):
        return False

    return True
            
def generate_uuid( digits ):
    """Generate a 'digits'-character hex endcoded string as
    a random identifier, with collision detection"""
    while True:    
        tmp = min(digits, 32)
        uid = uuid.uuid4().hex[:tmp]
        digits -= 32
        if digits <= 32:
            break

    return uid

ALPHABET = 'ZbDYFQLXx0PsHtmIcC2GA1qjB78VUdywJThkpnfWrOgSKu3olM59RizE64vNae'
def encode_base62(num):
    """Encode a number to base 62"""
    if num == 0:
        return ALPHABET[0]
    ret = []
    while num:
        rem = num % 62
        num = num // 62
        ret.append(ALPHABET[rem])
    ret.reverse()
    return ''.join(ret)


def get_request_variables(targets, rh):
    """Grab 'targets' from the request headers if present. Return
       a dictionary"""
    rd = {}
    for t in targets:
        rd[t] = rh.request.get(t) 
    return rd

# Cookie Stuff
def set_user_cookie(request_handler, user_uuid):
    """Sets a cookie to identify a user"""
    logging.info("Setting a user cookie: %s" % user_uuid)
    cookieutil = LilCookies(request_handler, COOKIE_SECRET)
    cookieutil.set_secure_cookie(name = 'willet_user_uuid', value = user_uuid, expires_days= 365*10)

def read_user_cookie( request_handler ):
    """Sets a cookie to identify a user"""
    cookieutil = LilCookies(request_handler, COOKIE_SECRET)
    user_uuid = cookieutil.get_secure_cookie(name = 'willet_user_uuid')
    logging.info("Reading a user cookie: %s" % user_uuid)
    return user_uuid

def set_referrer_cookie(headers, campaign_uuid, code):
    """Sets a referral cookie that signifies who referred this user """
    cookieUtil = Cookie.SimpleCookie()
    cookieUtil[str(campaign_uuid)] = code
    cookieUtil.name = str(campaign_uuid)
    cookieUtil[str(campaign_uuid)]['expires'] = 31556928
    
    headers.add_header('Set-Cookie', cookieUtil.output())

def set_clicked_cookie(headers, code):
    """Sets a cookie that signifies that this url has indeed been clicked"""
    cookieUtil = Cookie.SimpleCookie()
    cookieUtil[code] = True
    cookieUtil.name = code
    cookieUtil[code]['expires'] = 31556928
    
    headers.add_header('Set-Cookie', cookieUtil.output())

def set_referral_cookie(headers, code):
    """Sets a referral cookie that signifies that this user has been referred
       by the user that owns the link with url_willt_code == code"""
    cookieUtil = Cookie.SimpleCookie()
    cookieUtil['referral'] = code
    cookieUtil.name = 'referral'
    cookieUtil['referral']['expires'] = 31556928
    
    headers.add_header('Set-Cookie', cookieUtil.output())


def set_visited_cookie(headers):
    """Sets the approcity visited cookie so that registereud
       users are not presented with the 'register' tab again"""

    appCookie = Cookie.SimpleCookie()
    appCookie['willt-registered'] = True
    appCookie.name = "willt-registered"
    appCookie['willt-registered']['expires'] = 2629744
    headers['Set-Cookie'] = appCookie.output()

# Decorators
def login_required( fn ):
    def check(self, param=None):
        client = self.get_client()

        if client: 
            fn(self, client)
        else:
            self.redirect ( '/login?u=%s' % self.request.url )

    return check

def admin_required( fn ):
    def check(self, param=None):
        admin  = [ 'harrismc@gmail.com', 'z4beth@gmail.com', 'barbara@getwillet.com', 'barbara@wil.lt', 'fraser.harris@gmail.com'  ]
        client = self.get_client()

        if client and client.email in admin: 
            fn(self, client)
        else:
            self.redirect ( '/' )
    return check

#
# Click tracking helpers
# 
user_agent_blacklist = ['Voyager/1.0', 'Twitterbot/1.0', 'JS-Kit URL Resolver, http://js-kit.com/', 'ceron.jp', 
    'Mozilla/5.0 (compatible; MSIE 6.0b; Windows NT 5.0) Gecko/2009011913 Firefox/3.0.6 TweetmemeBot',
    'Jakarta Commons-HttpClient/3.1',
    'Crowsnest/0.5 (+http://www.crowsnest.tv/)',
    'Python-urllib/2.6',
    'Mozilla/5.0 (compatible; HiveAnalyzer http://www.businessinsider.com)',
    'trunk.ly spider contact@trunk.ly',
    'Squrl Java/1.6.0_22',
    'CURL/1.1',
    'PycURL/7.19.7', "Mozilla/5.0 (compatible; Yahoo! Slurp; http://help.yahoo.com/help/us/ysearch/slurp)",
    'MetaURI API/2.0 +metauri.com', 'Mozilla/5.0 (compatible; PaperLiBot/2.1)',
    'MLBot (www.metadatalabs.com/mlbot)', 'Mozilla/5.0 (compatible; Butterfly/1.0; +http://labs.topsy.com/butterfly/) Gecko/2009032608 Firefox/3.0.8',
    'Mozilla/5.0 (compatible; Birubot/1.0) Gecko/2009032608 Firefox/3.0.8', 'Mozilla/5.0 (compatible; PrintfulBot/1.0; +http://printful.com/bot.html)',
    'Summify (Summify/1.0.1; +http://summify.com)', 'LinkedInBot/1.0 (compatible; Mozilla/5.0; Jakarta Commons-HttpClient/3.1 +http://www.linkedin.com)',
    'Mozilla/5.0 (compatible; ScribdReader/1.0; +http://www.scribd.com/reader.html)', 'LongURL API', 'InAGist URL Resolver (http://inagist.com)',
    'Java/1.6.0_16', 'Java/1.6.0_26', 'Ruby', 'Twitturly / v0.6' 
    'Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10.6; en-US; rv:1.9.2) Gecko/20100115 Firefox/3.6 (FlipboardProxy/1.1; +http://flipboard.com/browserproxy)' ]

def is_blacklisted( header ):
    if 'bot' in header or 'Bot' in header or 'BOT' in header or len(header) == 0:
        return True
    else:
        return header in user_agent_blacklist

