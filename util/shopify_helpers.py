#!/usr/bin/env python

"""Supposed to contain Shopify-specific helpers."""
import urlparse

def get_shopify_url(shopify_url):
    """Formats a Shopify URL.

    Works for generic URLs as well.
    PyLint: Your code has been rated at -41.00/10
    """

    if not shopify_url:
        return ''

    if shopify_url[:4] != 'http':
        shopify_url = 'http://%s' % shopify_url  # assume no HTTPS

    if shopify_url.endswith('/'):
        shopify_url = shopify_url[:-1]

    return shopify_url

def get_url_variants(domain, keep_path=True):
    """Given a url, return it, as well as its similar domain with
    or without www.

    http://www.google.com   -> (http://google.com,
                                http://www.google.com)
    http://google.com       -> (http://google.com,
                                http://www.google.com)
    http://a.b.com          -> (http://a.b.com,
                                http://www.a.b.com)
    http://a.b.com/d/e.html -> (http://a.b.com/d/e.html,
                                http://www.a.b.com/d/e.html)

    keep_path = False will remove everything after the domain name.

    """

    if not domain:
        raise ValueError('Cannot get domain variants of nothing')

    if not (isinstance(domain, basestring) and isinstance(keep_path, bool)):
        raise TypeError('Parameters not of proper type')

    if not 'http://' in domain:
        domain = '%s%s' ('http://', domain)
    
    www_domain = domain
    ua = urlparse.urlsplit(domain)
    if len(ua.scheme) <= 0 or len(ua.netloc) <= 0:
        raise LookupError('domain supplied is not valid')

    # extra check for www.site.com
    if 'www.' in ua.netloc[:4]:  # url includes www.
        domain = "%s://%s" % (ua.scheme, ua.netloc[4:])  # remove www.
        www_domain = "%s://%s" % (ua.scheme, ua.netloc)  # keep www.
    else:  # url does not include www.
        domain = "%s://%s" % (ua.scheme, ua.netloc)  # do not add www.
        www_domain = "%s://www.%s" % (ua.scheme, ua.netloc)  # add www.

    # re-append path info if it is needed
    if keep_path:
        domain = "%s%s" % (domain, ua.path)
        www_domain = "%s%s" % (www_domain, ua.path)
        if ua.query:
            domain = "%s?%s" % (domain, ua.query)
            www_domain = "%s?%s" % (www_domain, ua.query)
        if ua.fragment:
            domain = "%s#%s" % (domain, ua.fragment)
            www_domain = "%s#%s" % (www_domain, ua.fragment)

    if not (domain and www_domain):
        raise ValueError('Not sure why, but not all arguments were processed')
    return (domain, www_domain)
