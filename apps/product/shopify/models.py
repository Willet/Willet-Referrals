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
    
    # A list of tags to describe the product
    tags = db.StringListProperty( indexed = False )

    def __init__(self, *args, **kwargs):
        super(ProductShopify, self).__init__(*args, **kwargs)
    
    @staticmethod
    def create_from_json(client, data, url=None):
        # Don't make it if we already have it
        product = ProductShopify.get_by_shopify_id( str( data['id'] ) )
        if not product:
            uuid = generate_uuid( 16 )

            images = []
            if 'images' in data:
                logging.debug ('%d images for this product found; adding to \
                    ProductShopify object.' % len(data['images']))
                images = [str(image['src']) for image in data['images']]
            
            # Make the product
            product = ProductShopify(
                    key_name     = uuid,
                    uuid         = uuid,
                    client       = client,
                    resource_url = url,
                    images       = images
            )

        # Now, update it with info.
        # update_from_json will PUT the obj.
        product.update_from_json(data)
        return product

    @classmethod
    def get_memcache_key (cls, unique_identifier):
        ''' unique_identifier can be URL or ID '''
        return '%s:%s' % (cls.__name__.lower(), str (unique_identifier))

    @classmethod
    def get_by_url(cls, url):
        
        data = memcache.get(ProductShopify.get_memcache_key(url))
        if data:
            product = db.model_from_protobuf(entity_pb.EntityProto(data))
        else:
            product = ProductShopify.all().filter('resource_url =', url).get()
        
        if product:
            product._memcache ()
        return product

    @classmethod
    def get_by_shopify_id(cls, id):
        id = str( id )
        data = memcache.get(cls.get_memcache_key(id))
        if data:
            product = db.model_from_protobuf(entity_pb.EntityProto(data))
        else:
            product = cls.all().filter('shopify_id =', id).get()
        
        if product:
            product._memcache ()
        return product

    @staticmethod
    def get_or_fetch(url, client):
        ''' returns a product from our datastore, or if it is not found, 
            fire a JSON request to Shopify servers to get the product's
            information, create the Product object, and returns that.
        '''
        url = url.split('?')[0].strip('/') # removes www.abc.com/product[/?junk=...]
        product = ProductShopify.get_by_url(url)
        if not product:
            if not product:
                logging.warn('Could not get product for url: %s' % url)
            try:
                # for either reason, we have to obtain the new product JSON
                result = urlfetch.fetch(
                        url = '%s.json' % url,
                        method = urlfetch.GET
                )
                # data is the 'product' key within the JSON object: http://api.shopify.com/product.html
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
        
        if type:
            self.type          = type
        if price != 0.0:
            self.price         = price
        if images:
            self.images        = images
        if description:
            self.description   = description
        if tags:
            self.tags          = tags

        if hasattr( self, 'processed' ):
            delattr( self, 'processed' )

        self.memcache ()
        self.put()

    def add_url(self, url):
        """ The Shopify API doesn't give us the URL for the product.
            Just add it here """
        self.resource_url = url
        self._memcache ()
        self.put()
    
    def _memcache (self):
        # updates all memcache for this item.
        self._memcache_by_url ()
        self._memcache_by_shopify_id ()
    
    def _memcache_by_url(self):
        """Memcaches this product by its url, False if memcache fails or if
        this product has no resource_url"""
        if hasattr(self, 'resource_url'):
            return memcache.set(
                    ProductShopify.get_memcache_key(self.resource_url), 
                    db.model_to_protobuf(self).Encode(),
                    time=MEMCACHE_TIMEOUT)
        return False

    def _memcache_by_shopify_id(self):
        ''' Stores the product by key product-shopify:(id).
            We call products by ID more so than we call by URL. '''
        if hasattr(self, 'shopify_id'):
            return memcache.set(
                    ProductShopify.get_memcache_key(self.shopify_id), 
                    db.model_to_protobuf(self).Encode(),
                    time=MEMCACHE_TIMEOUT)
        else:
            logging.warn ("cannot memcahce by shopify id")
        return False
