#!/usr/bin/env python

import logging

from django.utils import simplejson as json

from google.appengine.api import memcache
from google.appengine.ext import db
from apps.client.models import Client
# from apps.reengage.models import ReEngageQueue
from apps.reengage.social_networks import Facebook

from util.helpers import generate_uuid
from util.model import Model
from util.shopify_helpers import get_url_variants


class ProductCollection(Model, db.polymodel.PolyModel):
    """A "category" of sorts that binds multiple products under one roof.

    ProductShopifyCollection (subclass) contains functionality to automatically
    associate products with their collections.
    """

    # should NOT be accessed, use .products instead;
    # it is public only because GAE does not save underscored properties.
    product_uuids = db.StringListProperty(indexed=False)  # ['uuid', 'uuid', 'uuid']

    # name of this collection. indexed for get_by_client_and_name.
    collection_name = db.StringProperty(required=True, indexed=True)

    # Client.collections is a ReferenceProperty
    client = db.ReferenceProperty(db.Model, collection_name='collections')

    # use .queue to access this object (which autocreates a 1:1 queue)
    queue_ref = db.ReferenceProperty(db.Model)  # if you don't need it, don't use it

    def __init__(self, *args, **kwargs):
        self._memcache_key = kwargs['uuid'] if 'uuid' in kwargs else None
        super(ProductCollection, self).__init__(*args, **kwargs)

    def __str__(self):
        """String representation of the object."""
        return "%s %s" % (self.__class__, getattr(self, 'uuid', ''))

    def to_json(self):
        """JSON representation of the product object."""
        return json.dumps({
            'uuid': getattr(self, 'uuid', ''),
            'name': getattr(self, 'collection_name', ''),
            'shopify_id': unicode(getattr(self, 'shopify_id', '')),
            'shopify_handle': getattr(self, 'shopify_handle', ''),
            'products': [x.uuid for x in getattr(self, 'products', [])],  # could be nothing!
        })

    def _validate_self(self):
        if not self.client:
            raise AttributeError('ProductCollections must have Client')
        return True

    @staticmethod
    def create(**kwargs):
        """Creates a collection in the datastore using kwargs.

        In order to save as superclass (ProductCollection), all subclasses
        must implement this exact function. Also, ProductCollection must be
        a PolyModel.
        """
        kwargs['uuid'] = kwargs.get('uuid', generate_uuid(16))
        kwargs['key_name'] = kwargs.get('uuid')

        # patch for fake python property
        if kwargs.get('products', False):
            kwargs['product_uuids'] = [x.uuid for x in kwargs.get('products')]

        obj = ProductCollection(**kwargs)
        obj.put()

        return obj

    @classmethod
    def get_or_create(cls, **kwargs):
        """Looks up by kwargs[uuid], or creates one using the rest of kwargs
        if none found.
        """
        obj = cls.get(kwargs.get('uuid', ''))
        if obj:
            return obj

        client = Client.get(kwargs.get('client', None))
        if client:
            obj = cls.get_by_client_and_name(client,
                                             kwargs.get('collection_name', ''))
            if obj:
                return obj

        obj = cls.create(**kwargs)
        return obj

    @classmethod
    def get_by_client_and_name(cls, client, collection_name):
        """Returns the first collection from this client with this name."""
        return cls.all().filter('client =', client)\
                        .filter('collection_name =', collection_name).get()

    def _get_products(self):
        """GAE many-to-many relationship workaround allows getting, setting,
        and saving of products into collection objects directly.

        """
        return [Product.get(x) for x in self.product_uuids]

    def _set_products(self, value):
        """pass in a list of Product objects (subclasses allowed)."""
        self.product_uuids = list(frozenset([x.uuid for x in value]))

        # update the products too, I guess.
        for product in value:
            if not self.uuid in product.collection_uuids:
                product.collections.append(self)
                product.put_later()

    def _del_products(self):
        """empties the list (not deleting it)"""
        self.product_uuids = []

    # turn into attribute
    products = property(_get_products, _set_products, _del_products)


class Product(Model, db.polymodel.PolyModel):
    """Stores information about a store's product."""
    created = db.DateTimeProperty(auto_now_add=True)
    client = db.ReferenceProperty(Client, collection_name='products')

    # use .queue to access this object (which autocreates a 1:1 queue)
    queue_ref = db.ReferenceProperty(db.Model)  # if you don't need it, don't use it

    # should NOT be accessed, use .collections instead;
    # it is public only because GAE does not save underscored properties.
    collection_uuids = db.StringListProperty()  # ['uuid', 'uuid', 'uuid']

    description = db.TextProperty(default="")
    images = db.StringListProperty()  # list of urls to images
    price = db.FloatProperty(default=0.0)

    # product page url & main lookup key
    resource_url = db.StringProperty(default="")

    # A list of tags to describe the product
    tags = db.StringListProperty(indexed=False)
    title = db.StringProperty()  # name of the product
    type = db.StringProperty(indexed=False)  # The type of product

    # where a "reach" is defined as a comment/like/share about this product,
    # this score is the total of that.
    reach_score = db.IntegerProperty(default=0, indexed=True)

    _memcache_fields = ['resource_url', 'shopify_id']

    def __init__(self, *args, **kwargs):
        self._memcache_key = kwargs['uuid'] if 'uuid' in kwargs else None
        super(Product, self).__init__(*args, **kwargs)

    def __str__(self):
        """String representation of the product object."""
        return "%s %s" % (self.__class__, getattr(self, 'uuid', ''))

    def to_json(self):
        """JSON representation of the product object.

        {
            "products": [{
                "uuid": "a2a0e0c3f1f34c9b",
                "tags": ["Demo", " T-Shirt"],
                "shopify_id": "75473022",
                "client_uuid": "1b130711b754440e",
                "title": "Secured non-volatile challenge",
                "shopify_handle": "",
                "images": [],
                "resource_url": "",
                "type": "Shirts",
                "price": "19.0",
                "description": "<p>So this is a product.<\/p><p>The..."
            }]
        }
        """
        return json.dumps({
            'uuid': getattr(self, 'uuid', ''),
            'client_uuid': getattr(getattr(self, 'client', None), 'uuid', ''),
            'shopify_id': unicode(getattr(self, 'shopify_id', '')),
            'shopify_handle': getattr(self, 'shopify_handle', ''),
            'images': getattr(self, 'images', []),
            'description': getattr(self, 'description'),
            'price': unicode(getattr(self, 'price', '0')),
            'resource_url': getattr(self, 'resource_url', ''),
            'tags': getattr(self, 'tags', []),
            'title': getattr(self, 'title', ''),
            'type': getattr(self, 'type', ''),
        })

    def _validate_self(self):
        """Do some cleanup before saving."""
        self.title = self.title.strip()
        self.description = self.description.strip()

    @classmethod
    def _get_memcache_key (cls, unique_identifier):
        """ unique_identifier can be URL or ID """
        return '%s:%s' % (cls.__name__.lower(), str (unique_identifier))

    @staticmethod
    def create(title, description='', images=None, tags=None, price=0.0,
               client=None, resource_url='', type='', collection_uuids=None):
        """Creates a product in the datastore.
           Accepts datastore fields, returns Product object.
        """
        if images == None:
            images = []
        if tags == None:
            tags = []

        # set uuid to its most "useful" hash.
        try:
            uu_format = "%s-%s" % (client.domain, title)
        except AttributeError, err:
            uu_format = generate_uuid(16)
        uuid = Product.build_secondary_key(uu_format)

        product = Product(key_name=uuid,
                          uuid=uuid,
                          title=title,
                          description=description,
                          images=images,
                          price=price,
                          client=client,
                          type=type,
                          tags=tags,
                          collection_uuids=collection_uuids or [])
        product.resource_url = resource_url # apparently had to be separate
        product.put()
        return product

    @staticmethod
    def get_or_create(title, description='', images=None, tags=None, price=0.0,
                      client=None, resource_url='', type='', uuid=''):
        """Tries to look up a product.

        If none is found, create based on the same parameters.
        client is actually required.
        """
        if images == None:
            images = []
        if tags == None:
            tags = []

        product = Product.get(uuid)
        if product:
            return product

        product = Product.get_by_url(resource_url)
        if product:
            return product

        if client and client.domain and title:  # can check for existence
            uu_format = "%s-%s" % (client.domain, title)
            uuid = Product.build_secondary_key(uu_format)
            product = Product.get(uuid)
            if product:
                return product

        product = Product.create(title=title,
                                 description=description,
                                 images=images,
                                 price=price,
                                 client=client,
                                 resource_url=resource_url,
                                 type=type,
                                 tags=tags)
        return product

    @classmethod
    def get_by_url(cls, url):
        """Retrieves a Product or its subclass instance by resource_url."""
        www_url = url

        if not url:
            return None  # can't get by url if no URL given

        urls = get_url_variants(url, keep_path=True)

        for url2 in urls:
            data = memcache.get(cls._get_memcache_key(url2))
            if data:
                return db.model_from_protobuf(entity_pb.EntityProto(data))

        for url2 in urls:
            data = memcache.get(url2)
            if data:
                return db.model_from_protobuf(entity_pb.EntityProto(data))

        product = cls.all().filter('resource_url IN', urls).get()
        return product

    @classmethod
    def get_or_fetch(cls, url, client):
        """Returns a product from our datastore.

        If the product cannot be found in the datastore, various methods will
        be used to retrieve the product. The return object class will be that
        resulted from a successful fetch.

        Examples:
            - in DB -> Product
            - not in DB, fetch like ProductShopify succeeds: ProductShopify
                (returned as Product)
            - not in DB, fetch like ProductShopify fails: None
        """
        # put there to prevent circular reference
        from apps.product.shopify.models import ProductShopify

        # remove www.abc.com/product[/?junk=...]
        url = url.split('?')[0].strip('/')

        product = Product.get_by_url(url)
        if not product:
            product = ProductShopify.get_or_fetch(url, client)

        return product

    def _get_collections(self):
        """GAE many-to-many relationship workaround allows getting, setting,
        and saving of collections into product objects directly.

        """
        return [ProductCollection.get(x) for x in self.collection_uuids]

    def _set_collections(self, value):
        """pass in a list of ProductCollection objects (subclasses allowed)."""
        self.collection_uuids = list(frozenset([x.uuid for x in value]))

        # update the products too, I guess.
        for collection in value:
            if not self.uuid in collection.product_uuids:
                collection.products.append(self)
                collection.put_later()

    def _del_collections(self):
        """empties the list (not deleting it)"""
        self.collection_uuids = []

    # turn into attribute
    collections = property(_get_collections, _set_collections, _del_collections)

    def get_facebook_reach(self, force=False, url=''):
        """use the Facebook request class to retrieve the number of shares/
        comments/what_have_you for this product. If the product has a url
        (resource_url), it will be used for the query.

        If force is true or cached reach is 0, then this product will have its
        reach re-fetched every time this function is called.

        Default: 0
        """
        # check if reach score is already there, and return it unless
        # it is being forced.
        if not force and getattr(self, 'reach_score', 0) > 0:
            logging.info('product already has a reach score'
                         ' (%d)' % self.reach_score)
            return self.reach_score

        url = url or getattr(self, 'resource_url', '')
        if not url:
            logging.info('product has no url; cannot get reach score.')
            return 0
        reach_count = int(Facebook.get_reach_count(url)) or 0

        logging.info('saving reach of %d' % reach_count)
        self.reach_score = reach_count
        self.put_later()

        return reach_count

    def _get_or_create_queue(self):
        """return a queue that corresponds to this product."""
        logging.debug('called _get_or_create_queue')
        try:
            if self.queue_ref:
                logging.debug('found built-in ref')
                return self.queue_ref
        except db.ReferencePropertyResolveError, err:
            pass

        # could not import globally :(
        if not self.client:
            raise AttributeError('cannot make queue for None-client product')

        from apps.reengage.models import ReEngageQueue, ReEngageShopify
        queue_name = self._get_associated_queue_name()
        queue = ReEngageQueue.get_by_client_and_name(self.client,
                                                    queue_name)
        logging.debug('got queue? %r' % queue)
        if queue:  # found queue, use it
            logging.debug('returning %r' % queue)
            return queue

        # queue not found, suck it up and return one
        logging.debug('found nothing of significance')
        app = ReEngageShopify.get_by_client_and_name(self.client,
                                                    'ReEngageShopify')
        logging.debug('got app? %r' % app)
        queue = ReEngageQueue.create(app_=app,
                                        name=queue_name,
                                        product_uuids=[self.uuid],
                                        uuid=generate_uuid(16))
        self.queue_ref = queue
        self.put_later()
        logging.debug('returning queue %r' % queue)
        return queue

    # turn into attribute
    queue = property(_get_or_create_queue)

    def _get_associated_queue_name(self):
        """."""
        queue_name = '%s-%s-%s' % ('ReEngageQueue',
                                   self.__class__.__name__,
                                   self.uuid)
        return queue_name
