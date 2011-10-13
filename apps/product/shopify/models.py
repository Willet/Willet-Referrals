#!/usr/bin/env python

import logging
from datetime import datetime

from django.utils               import simplejson as json
from google.appengine.api       import urlfetch
from google.appengine.ext import db

from apps.product.models import Product

class ProductShopify(Product):
    
    shopify_id = db.StringProperty()

    # this is the URL used to lookup this product
    resource_url = db.StringProperty()
    
    # cache the json result so we can get more fields later
    json_response = db.TextProperty()

    last_fetch = db.DateTimeProperty()

    def __init__(self, *args, **kwargs):
        super(ProductShopify, self).__init__(*args, **kwargs)
    
    def update_from_json(self):
        response = False
        try:
            data = json.loads(self.json_response)['product']

            # remove all newlines from description
            description = data['body_html']\
                    .replace('\r\n', '')\
                    .replace('\n', '')

            # create a list of urls to images
            images = [image['src'] for image in data['images']]
            self.shopify_id = str(data['id'])
            self.title = data['title']
            self.price = float(data['variants'][0]['price'])
            self.images = images
            self.description = description
            self.put()
            response = True
        except:
            logging.error('error updating from json\n%s\n%s' % (
                    self.json_response,
                    self.resource_url
                ),
                exc_info=True
            )
        return response

    def refetch(self):
        """Uses the internal resource_url to refetch the json and load data"""
        response = False
        try:
            result = urlfetch.fetch(
                url = '%s.json' % self.resource_url,
                method = urlfetch.GET
            )
            
            self.last_fetch = datetime.now()
            self.json_response = result.content
            self.update_from_json()
            response = True
        except:
            logging.error('error refetching: %s' % self.resource_url, exc_info=True)
        return response

def get_shopify_product_by_url(url):
    return ProductShopify.all().filter('resource_url =', url).get()

def get_shopify_product_by_id(id):
    return ProductShopify.all().filter('shopify_id =', id).get()

def get_or_create_shopify_product_by_id(id, **kwargs):
    product = get_shopify_product_by_id(id) 
    if product == None:
        product = ProductShopify(
            shopify_id = id,
            **kwargs
        )
        product.put()

    return product

def get_or_create_shopify_product_by_url(url, **kwargs):
    product = get_shopify_product_by_url(url) 
    if product == None:
        product = ProductShopify(
            resource_url = url,
            **kwargs
        )
        product.put()

    return product

def get_or_fetch_shopify_product(url, client):
    product = get_shopify_product_by_url(url)
    if product == None:
        try:
            result = urlfetch.fetch(
                    url = '%s.json' % url,
                    method = urlfetch.GET
            )
                        
            # create product
            product = ProductShopify(
                last_fetch = datetime.now(),
                resource_url = url,
                client = client,
                json_response = result.content 
            )
            product.update_from_json()
        except:
            logging.error("error fetching and storing product for url %s" % url, exc_info=True)
    return product

