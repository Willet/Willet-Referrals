#!/usr/bin/env python

import logging
from datetime import datetime

from django.utils               import simplejson as json
from google.appengine.api       import urlfetch
from google.appengine.ext import db

from apps.product.models import Product
from util.helpers import generate_uuid

class ProductShopify(Product):
    
    processed = db.BooleanProperty( default = False, indexed = True )

    shopify_id = db.StringProperty( indexed = True )

    # this is the URL used to lookup this product
    # this will be filled in when people view product pages
    resource_url = db.StringProperty( default = "" )
    
    # cache the json result so we can get more fields later
    json_response = db.TextProperty( indexed = False )

    # The type of product
    type = db.StringProperty( indexed = False )

    # A list of tags to describe the product
    tags = db.StringListProperty( indexed = False )

    def __init__(self, *args, **kwargs):
        super(ProductShopify, self).__init__(*args, **kwargs)
    
    @staticmethod
    def create_from_json(client, data, url=None):
        # Don't make it if we already have it
        if ProductShopify.get_by_shopify_id( str( data['id'] ) ) != None:
            return

        uuid = generate_uuid( 16 )
        
        # Make the product
        product = ProductShopify(
                key_name = uuid,
                uuid = uuid,
                client = client,
                resource_url = url
        )

        # Now, update it with info.
        # update_from_json will PUT the obj.
        product.update_from_json(data)
        return product

    @staticmethod
    def get_by_url(url):
        return ProductShopify.all().filter('resource_url =', url).get()

    @staticmethod
    def get_by_shopify_id(id):
        id = str( id )
        return ProductShopify.all().filter('shopify_id =', id).get()

    @staticmethod
    def get_or_fetch(url, client):
        product = ProductShopify.get_by_url( url )
        if product == None:
            logging.warn('Could not get product for url: %s' % url)
            try:
                result = urlfetch.fetch(
                        url = '%s.json' % url,
                        method = urlfetch.GET
                )
                            
                data = json.loads(result.content)['product']
                product = ProductShopify.get_by_shopify_id( str(data['id']) )
                if product:
                    product.add_url(url)
                else:
                    logging.error('failed to get product for id: %s' % str(data['id']))
                    product = ProductShopify.create_from_json(client, data, url=url)
            except:
                logging.error("error fetching and storing product for url %s" % url, exc_info=True)
        return product

    def update_from_json(self, data):
        logging.info("data %s" % data)
        tags = description = images = None
        price = 0.0

        # remove all newlines from description
        try:    
            description = data['body_html']\
                    .replace('\r\n', '')\
                    .replace('\n', '')
        except:
            logging.info("No desc for this product %s" % self.uuid)

        # create a list of urls to images
        try:
            images = [image['src'] for image in data['images']]
        except:
            logging.info("No images for this product %s" % self.uuid)

        try:
            price = float(data['variants'][0]['price'])
        except:
            logging.info("No price for this product %s" % self.uuid)

        try:
            tags = data[ 'tags' ].split(',')
        except:
            logging.info("No tags for this product %s" % self.uuid)

        # Update the Product
        self.shopify_id    = str(data['id'])
        self.title         = data['title']
        self.price         = price
        self.images        = images
        self.description   = description
        self.type          = data[ 'product_type' ]
        self.tags          = tags
        self.json_response = json.dumps( data )

        self.put()

    def add_url(self, url):
        """ The Shopify API doesn't give us the URL for the product.
            Just add it here """
        self.resource_url = url
        self.put()

