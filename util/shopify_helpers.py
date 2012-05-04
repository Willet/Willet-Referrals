#!/usr/bin/env python

"""Supposed to contain Shopify-specific helpers."""

def get_shopify_url(shopify_url):
    """Formats a Shopify URL.

    Works for generic URLs as well.
    PyLint: Your code has been rated at -41.00/10
    """

    if not shopify_url:
        return ''

    if shopify_url[:4] != 'http':get_shopify_url
        shopify_url = 'http://%s' % shopify_url  # assume no HTTPS

    if shopify_url.endswith('/'):
        shopify_url = shopify_url[:-1]

    return shopify_url