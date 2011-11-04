#!/usr/bin/env python

import hashlib, logging, urllib, urllib2, uuid, re, Cookie, os

from datetime import datetime
from django.utils import simplejson as json

from google.appengine.api import memcache, taskqueue, urlfetch
from google.appengine.ext import db, webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

from apps.client.models import Client
from apps.product.shopify.models import ProductShopify

from util.consts import *
from util.helpers import *
from util.urihandler import URIHandler

class FetchProductShopify(webapp.RequestHandler):
    """Fetch shopify product"""
    def post(self):

        url = self.request.get('url')
        client_uuid = self.request.get('client')
        client = Client.all().filter('uuid =', client_uuid).get()

        logging.info('getting url: %s' % url)

        product = ProductShopify.get_or_fetch(url, client)
        
        logging.info("done updating %s" % product)

