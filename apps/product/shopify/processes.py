#!/usr/bin/env python

import hashlib, logging, urllib, urllib2, uuid, re, Cookie, os

from datetime import datetime
from django.utils import simplejson as json

from google.appengine.api import memcache, taskqueue, urlfetch
from google.appengine.ext import db, webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

from apps.client.shopify.models import ClientShopify
from apps.product.shopify.models import ProductShopify

from util.consts import *
from util.helpers import *
from util.shopify_helpers import get_shopify_url
from util.urihandler import URIHandler

class CreateProductShopify( URIHandler ):
    """Create a Shopify product"""
    def post(self):
        logging.info("HEADERS : %s %r" % (
            self.request.headers,
            self.request.headers
            )
        )

        store_url = get_shopify_url(self.request.headers['X-Shopify-Shop-Domain'])
        logging.info("store: %s " % store_url)
        client = ClientShopify.get_by_url( store_url ) 

        # Grab the data about the product from Shopify
        product = json.loads(self.request.body) 

        ProductShopify.create_from_json( client, product )

class UpdateProductShopify( URIHandler ):
    """Update a Shopify product"""
    def post(self):
        logging.info("HEADERS : %s %r" % (
            self.request.headers,
            self.request.headers
            )
        )

        store_url = "http://%s" % self.request.headers['X-Shopify-Shop-Domain']
        logging.info("store: %s " % store_url)
        store_url = get_shopify_url(self.request.headers['X-Shopify-Shop-Domain'])

        # Grab the data about the product from Shopify
        data = json.loads(self.request.body) 
        product = ProductShopify.get_by_shopify_id( str(data['id']) )
        
        if product:
            product.update_from_json( data )
        else:
            client = ClientShopify.get_by_url( store_url ) 
            ProductShopify.create_from_json( client, data )

class DeleteProductShopify( URIHandler ):
    """Delete a Shopify product"""
    def post(self):
        logging.info("HEADERS : %s %r" % (
            self.request.headers,
            self.request.headers
            )
        )

        # Grab the data about the product from Shopify
        data = json.loads(self.request.body) 

        product = ProductShopify.get_by_shopify_id( str( data['id'] ) )
        
        # Delete the product from our DB.
        if product:
            product.delete()
