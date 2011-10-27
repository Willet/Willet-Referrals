#!/usr/bin/env python

import cgi, hashlib, re, os, logging, urllib, urllib2, uuid, Cookie
import sys

from util.consts  import *

def get_shopify_url( url ):
    if url[:7] != 'http://':
        url = 'http://%s' % url 

    if url.endswith( '/' ):
        l = len( url )
        url = url[ l - 1 ]

    return url
