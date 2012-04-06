#!/usr/bin/env python

import cgi, hashlib, re, os, logging, urllib, urllib2, uuid, Cookie
import sys

from util.consts import *

def get_shopify_url(shopify_url):
    if shopify_url[:7] != 'http://':
        shopify_url = 'http://%s' % shopify_url 

    if shopify_url.endswith('/'):
        l = len(shopify_url)
        shopify_url = shopify_url[ l - 1 ]

    return shopify_url