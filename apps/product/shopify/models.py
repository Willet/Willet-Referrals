#!/usr/bin/env python

import logging

from django.utils               import simplejson as json
from google.appengine.api       import urlfetch
from google.appengine.ext import db
from google.appengine.api import memcache
from google.appengine.datastore import entity_pb

from apps.product.models        import Product
from util.helpers               import generate_uuid
from util.consts import MEMCACHE_TIMEOUT

class ProductShopify(Product):
    
    shopify_id = db.StringProperty( indexed = True )

    # this is the URL used to lookup this product
    # this will be filled in when people view product pages
    resource_url = db.StringProperty( default = "" )
    
    # cache the json result so we can get more fields later
    json_response = db.TextProperty( indexed = False )

    # The type of product
    type = db.StringProperty( indexed = False )

    # Array of IDs of the variants of the product
    # (get from shopify API: /admin/products.json)
    variants = db.ListProperty(int, indexed = False)

    # A list of tags to describe the product
    tags = db.StringListProperty( indexed = False )

    def __init__(self, *args, **kwargs):
        super(ProductShopify, self).__init__(*args, **kwargs)
    
    @staticmethod
    def create_from_json(client, data, url=None):
        # Don't make it if we already have it
        product = ProductShopify.get_by_shopify_id( str( data['id'] ) )
        if product == None:
            uuid = generate_uuid( 16 )
            
            variants = []
            if 'variants' in data:
                # if one or more variants exist, store their IDs. 
                # otherwise, store an empty list.
                logging.debug ('%d variants for this product found; adding to ProductShopify object.' % len(data['variants']))
                variants = [variant['id'] for variant in data['variants']]
            logging.info ('variants = %s' % variants)
            
            # Make the product
            product = ProductShopify(
                    key_name     = uuid,
                    uuid         = uuid,
                    client       = client,
                    resource_url = url,
                    variants     = variants
            )

        # Now, update it with info.
        # update_from_json will PUT the obj.
        product.update_from_json(data)
        return product

    @staticmethod
    def get_memcache_key(url):
        return 'product-shopify:%s' % url

    @staticmethod
    def get_by_url(url):
        # TODO: Enable this when we have a way to edit/upate memcahce
        """
        data = memcache.get(ProductShopify.get_memcache_key(url))
        if data:
            product = db.model_from_protobuf(entity_pb.EntityProto(data))
        else:
        """
        product = ProductShopify.all().filter('resource_url =', url).get()
        if product:
            product.memcache_by_url()
        return product

    @staticmethod
    def get_by_shopify_id(id):
        id = str( id )
        return ProductShopify.all().filter('shopify_id =', id).get()

    @staticmethod
    def get_or_fetch(url, client):
        product = ProductShopify.get_by_url(url)
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
                    logging.warn('failed to get product for id: %s; creating one.' % str(data['id']))
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

        type = data[ 'product_type' ]


        # Update the Product
        self.shopify_id    = str(data['id'])
        self.title         = data[ 'title' ]
        self.json_response = json.dumps( data )
        
        if len(type) != 0:
            self.type          = type
        if price != 0.0:
            self.price         = price
        if images != None and len(images) != 0:
            self.images        = images
        if description != None and len(description) != 0:
            self.description   = description
        if tags != None and len(tags) != 0:
            self.tags          = tags

        if hasattr( self, 'processed' ):
            delattr( self, 'processed' )

        self.put()

    def add_url(self, url):
        """ The Shopify API doesn't give us the URL for the product.
            Just add it here """
        self.resource_url = url
        self.memcache_by_url()
        self.put()

    def memcache_by_url(self):
        """Memcaches this product by its url, False if memcache fails or if
        this product has no resource_url"""
        if hasattr(self, 'resource_url'):
            return memcache.set(
                    ProductShopify.get_memcache_key(self.resource_url), 
                    db.model_to_protobuf(self).Encode(),
                    time=MEMCACHE_TIMEOUT)
        return False

