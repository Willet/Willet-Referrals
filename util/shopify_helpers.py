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

def get_domain(url):
    """Extract the domain from a URL. Will not come with trailing slash.

    Example output: http://google.com

    Commonly, AttributeErrors are raised if the url itself is invalid.
    """
    parts = urlparse.urlparse(url)
    if not (parts.scheme and parts.netloc):
        raise AttributeError('Invalid URL')
    return '%s://%s' % (parts.scheme, parts.netloc)


def get_url_variants(domain, keep_path=True):
    """Given a url, return it, as well as its similar domain with
    or without www.

    http://www.google.com   -> [http://google.com,
                                http://www.google.com,
                                https://google.com,
                                https://www.google.com]
    http://google.com       -> [http://google.com,
                                http://www.google.com,
                                https://google.com,
                                https://www.google.com]
    http://a.b.com          -> [http://a.b.com,
                                http://www.a.b.com,
                                https://a.b.com,
                                https://www.a.b.com]
    http://a.b.com/d/e.html -> [http://a.b.com/d/e.html,
                                http://www.a.b.com/d/e.html,
                                https://a.b.com/d/e.html,
                                https://www.a.b.com/d/e.html]

    keep_path = False will remove everything after the domain name.

    """

    if not domain:
        raise ValueError('Cannot get domain variants of nothing')

    if not (isinstance(domain, basestring) and isinstance(keep_path, bool)):
        raise TypeError('Parameters not of proper type')

    www_domain = domain
    ua = urlparse.urlsplit(domain)
    if len(ua.scheme) <= 0:
        ua_scheme = 'http'  # most likely doing things like 'kiehn-mertz.com'
        ua_netloc = ua.path  # if scheme is missing, netloc is shifted to path
    else:
        ua_scheme = ua.scheme
        ua_netloc = ua.netloc

    # extra check for www.site.com
    if 'www.' in ua_netloc[:4]:  # url includes www.
        domain = "%s://%s" % ('http', ua_netloc[4:])  # remove www.
        www_domain = "%s://%s" % ('http', ua_netloc)  # keep www.
        domain2 = "%s://%s" % ('https', ua_netloc[4:])  # remove www.
        www_domain2 = "%s://%s" % ('https', ua_netloc)  # keep www.
    else:  # url does not include www.
        domain = "%s://%s" % ('http', ua_netloc)  # do not add www.
        www_domain = "%s://www.%s" % ('http', ua_netloc)  # add www.
        domain2 = "%s://%s" % ('https', ua_netloc)  # do not add www.
        www_domain2 = "%s://www.%s" % ('https', ua_netloc)  # add www.

    # re-append path info if it is needed
    if keep_path:
        domain = "%s%s" % (domain, ua.path)
        www_domain = "%s%s" % (www_domain, ua.path)
        domain2 = "%s%s" % (domain2, ua.path)
        www_domain2 = "%s%s" % (www_domain2, ua.path)
        if ua.query:
            domain = "%s?%s" % (domain, ua.query)
            www_domain = "%s?%s" % (www_domain, ua.query)
            domain2 = "%s?%s" % (domain2, ua.query)
            www_domain2 = "%s?%s" % (www_domain2, ua.query)
        if ua.fragment:
            domain = "%s#%s" % (domain, ua.fragment)
            www_domain = "%s#%s" % (www_domain, ua.fragment)
            domain2 = "%s#%s" % (domain2, ua.fragment)
            www_domain2 = "%s#%s" % (www_domain2, ua.fragment)

    if not (domain and www_domain and domain2 and www_domain2):
        raise ValueError('Not sure why, but not all arguments were processed')
    return [domain, www_domain, domain2, www_domain2]