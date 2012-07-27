#!/usr/bin/env python

"""Bunch of helper functions that everyone might want to use."""

import Cookie
import hashlib
import logging
import re
import urllib
import uuid

from urlparse import urlparse

from google.appengine.ext import db, webapp

from util.consts import *
from util.cookies import LilCookies


ALPHABET = 'ZbDYFQLXx0PsHtmIcC2GA1qjB78VUdywJThkpnfWrOgSKu3olM59RizE64vNae'


def default(*args):
    """Retrieves the first non-None variable in *args.

    An exception is caught, ignored, and treated as None.
    If none of the supplied variables are available,
    this function returns None or ENV_FUNC_RETVAL.

    >>> print default()
    None
    >>> print default(1)
    1
    >>> print default(0,1)
    0
    >>> print default(None,1)
    1
    >>> print default(None,False,0)
    False
    """
    for arg in args:
        try:
            if arg != None:
                return arg
        except:
            pass  # fail? do not return this one


def quoted_join(lst):
    """Returns "1","2","3"."""
    return '"%s"' % '","'.join(lst)


def to_dict(something, recursion=0):
    """Converts an object into a dictionary.

    Converted dictionary is serializable; if an attribute is an object, the
    object will be recursively converted to a dictionary as well.
    """
    import datetime
    import time
    output = {}

    SIMPLE_TYPES = (int, long, float, bool, dict, basestring, list)
    if recursion > 3:
        logging.error('recursion too much, returning: %s' % str(something))
        return str(something)

    for key, prop in something.properties().iteritems():
        value = getattr(something, key)
        logging.debug('processing: %s' % key)

        try:
            if value is None or isinstance(value, SIMPLE_TYPES):
                output[key] = value
            elif isinstance(value, datetime.date) or \
                    isinstance(value, datetime.datetime):
                # Convert date/datetime to ms-since-epoch ("new Date()").
                ms = time.mktime(value.utctimetuple()) * 1000
                ms += getattr(value, 'microseconds', 0) / 1000
                output[key] = int(ms)
            elif isinstance(value, db.GeoPt):
                output[key] = {'lat': value.lat, 'lon': value.lon}
            elif isinstance(value, db.Model):
                output[key] = to_dict(value, recursion=recursion+1)
            else:
                output[key] = str(value)
                logging.error('weird value: %s' % str(value))
                #raise ValueError('cannot encode ' + repr(prop))
        except Exception, e:
            logging.error(e, exc_info=True)
    return output


def common_items(list1, list2):
    """Returns the items present in both lists."""
    return frozenset(list1) & frozenset(list2)


def get_target_url(referrer):
    """ Clean up a URL to only contain protocol://domain.com/file.htm """
    target = ""
    if referrer:
        try:
            # urlparse raises errors if referrer is None (impossible here)
            page_url = urlparse(referrer)
            if page_url.scheme and page_url.netloc:
                target = "%s://%s%s" % (page_url.scheme, page_url.netloc,
                                        page_url.path)
        except Exception, e:
            logging.warn('error parsing referer %s: %s' % (referrer,e),
                         exc_info=True)
    return target


def generate_uuid(digits):
    """I am guessing this is a wrapper for uuid4."""
    if digits > 32:
        raise ValueError('max UUID length is 32')

    return uuid.uuid4().hex[:digits]


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


def cast(variable, rtype, raise_exception=True):
    """Returns the variable of required type.

    variable: the variable
    rtype: a type-function, e.g. bool, int, str; or
           a list of variable types.
    raise_exception: True will raise a ValueError if the variable is not of
                     the required type.
                     False will attempt to convert the variable to the
                     required type, returning the original variable if
                     conversion fails.
    Variable type enforcement is not pythonic, but all the libraries do it
    (e.g. see behaviour in urlparse)

    """
    if isinstance(rtype, list):
        # map-reduce to see if any condition is met
        return reduce(lambda x, y: x or y,
                      map(cast,
                          [variable] * len(rtype),
                          rtype,
                          [raise_exception] * len(rtype)))

    if isinstance(variable, rtype):
        return variable

    # so, it is not of the required type
    if raise_exception:
        raise ValueError('Variable not of requird type')

    # not of required type, but want conversion done
    try:
        return rtype(variable)
    except:
        return variable  # conversion failed; oh well


# Cookie Stuff
def set_user_cookie(request_handler, user_uuid):
    """Sets a cookie to identify a user"""
    logging.info("Setting a user cookie: %s" % user_uuid)
    cookieutil = LilCookies(request_handler, COOKIE_SECRET)
    #cookieutil.set_secure_cookie(
    #        name = 'willet_user_uuid',
    #        value = user_uuid,
    #        expires_days= 365*10)
    cookieutil.set_secure_cookie(
            name = 'willet_user_uuid',
            value = user_uuid,
            expires_days= 365*10,
            domain = '.%s' % APP_DOMAIN)


def read_user_cookie(request_handler):
    """Sets a cookie to identify a user"""
    cookieutil = LilCookies(request_handler, COOKIE_SECRET)
    user_uuid = cookieutil.get_secure_cookie(name = 'willet_user_uuid')
    logging.debug("Reading a user cookie: %s" % user_uuid)
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
def admin_required(fn):
    def check(self, param=None):
        from apps.user.models import User
        user_cookie = read_user_cookie(self)
        user = User.get(user_cookie) if user_cookie else None

        try:
            if not user or not user.is_admin():
                logging.error('@admin_required: Non-admin is attempting to access protected pages')
                self.redirect ('/')
                return
            else:
                fn(self, param)
        except Exception, e:
            logging.error('@admin_required - Error occured, redirecting to homepage: %s' % e, exc_info=True)
            self.redirect ('/')
            return
    return check

# Click tracking helpers
user_agent_blacklist = ['Voyager/1.0', 'Twitterbot/1.0', 'JS-Kit URL Resolver, http://js-kit.com/', 'ceron.jp',
    'Mozilla/5.0 (compatible; MSIE 6.0b; Windows NT 5.0) Gecko/2009011913 Firefox/3.0.6 TweetmemeBot',
    'Jakarta Commons-HttpClient/3.1',
    'Crowsnest/0.5 (+http://www.crowsnest.tv/)',
    'Python-urllib/2.6',
    'Mozilla/5.0 (compatible; HiveAnalyzer http://www.businessinsider.com)',
    'trunk.ly spider contact@trunk.ly',
    'Squrl Java/1.6.0_22',
    'CURL/1.1',
    'facebookexternalhit/1.1',
    'ia_archiver',
    'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
    'PycURL/7.19.7', "Mozilla/5.0 (compatible; Yahoo! Slurp; http://help.yahoo.com/help/us/ysearch/slurp)",
    'MetaURI API/2.0 +metauri.com', 'Mozilla/5.0 (compatible; PaperLiBot/2.1)',
    'MLBot (www.metadatalabs.com/mlbot)', 'Mozilla/5.0 (compatible; Butterfly/1.0; +http://labs.topsy.com/butterfly/) Gecko/2009032608 Firefox/3.0.8',
    'Mozilla/5.0 (compatible; Birubot/1.0) Gecko/2009032608 Firefox/3.0.8', 'Mozilla/5.0 (compatible; PrintfulBot/1.0; +http://printful.com/bot.html)',
    'Summify (Summify/1.0.1; +http://summify.com)', 'LinkedInBot/1.0 (compatible; Mozilla/5.0; Jakarta Commons-HttpClient/3.1 +http://www.linkedin.com)',
    'Mozilla/5.0 (compatible; ScribdReader/1.0; +http://www.scribd.com/reader.html)', 'LongURL API', 'InAGist URL Resolver (http://inagist.com)',
    'Java/1.6.0_16', 'Java/1.6.0_26', 'Ruby', 'Twitturly / v0.6'
    'Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10.6; en-US; rv:1.9.2) Gecko/20100115 Firefox/3.6 (FlipboardProxy/1.1; +http://flipboard.com/browserproxy)' ]

def is_blacklisted(header):
    if 'bot' in header or 'Bot' in header or 'BOT' in header or len(header) == 0:
        return True
    else:
        return header in user_agent_blacklist


def url(view, *args, **kwargs):
    """
    looks up a url for a view
        - view is a string, name of the view (such as ShowRoutes)
        - args are optional parameters for that view
            for handlers with wildcards (capture groups), args is used to
            fill in those groups.
        - **kwargs takes a named argument qs. qs is passed to
            urllib.urlencode and tacked on to the end of the url
            Basically, use this to pass a dict of arguments
        example usage: url('ShowDashboard', '12512512', qs={'order': 'date'})
            - this would return a url to the ShowDashboard view, for the
              dashboard id 12512512, and pass the order=date
            - /app/12512512/?order=date
        example: url('ShowProfilePage', '1252', '2151', qs={'format':'json'})
            - /user/1252/2151/?format=json
    """
    url = None
    try:
        app = webapp.WSGIApplication.active_instance
        handler = app.get_registered_handler_by_name(view)

        url = handler.get_url(*args)

        qs = kwargs.get('qs', ())
        if qs:
            url += '?%s' % urllib.urlencode(qs)

        # logging.info('url(\'%s\',...) became: %s' % (view, url))
    except:
        logging.warn('Could not reverse url %s' % view)

    return url


def remove_html_tags(data):
    p = re.compile(r'<.*?>')
    return p.sub('', data)


def create_hash(*args):
    """Returns a hash from args"""
    keys = list (args)
    if SALT:
        keys.append (SALT)
    key = "".join(list(('%s$' % str(k)) for k in keys))
    return hashlib.sha224(key).hexdigest()

def unhashable_object_unique_filter(objects, attr='uuid'):
    """Supply objects, returns objects whose attributes reflect uniqueness.

    attr should be a unique field, and MUST be present in all objects.

    Example:
        Model1.uuid = 1
        Model2.uuid = 2
        Model3.uuid = 3
        Model4.uuid = 3
        unhashable_object_unique_filter([Model1, Model2, Model3, Model3])
        => [Model1, Model2, Model3].
    """
    attrs = []
    filtered_objs = []

    for obj in objects:
        if obj:  # rid None
            if not getattr(obj, attr) in attrs:
                filtered_objs.append(obj)
                attrs.append(getattr(obj, attr))

    return filtered_objs
