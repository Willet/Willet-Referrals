#!/usr/bin/env python

import logging

from google.appengine.api import memcache
from google.appengine.ext import db
from apps.client.models import Client

from util.helpers import generate_uuid
from util.model import Model
from util.shopify_helpers import get_url_variants


class ProductCollection(Model):
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
    client = db.ReferenceProperty(Client, collection_name='collections')

    def __init__(self, *args, **kwargs):
        self._memcache_key = kwargs['uuid'] if 'uuid' in kwargs else None
        super(ProductCollection, self).__init__(*args, **kwargs)

    def _validate_self(self):
        if not self.client:
            raise AttributeError('ProductCollections must have Client')
        return True

    @classmethod
    def create(cls, **kwargs):
        """Creates a collection in the datastore using kwargs.

        Subclasses will have different field requirements.

        It will raise its own error if
        - you do not supply the appropriate fields, or
        - you give it too many fields.
        """
        kwargs['uuid'] = kwargs.get('uuid', generate_uuid(16))
        kwargs['key_name'] = kwargs.get('uuid')

        # patch for fake python property
        if kwargs.get('products', False):
            kwargs['product_uuids'] = [x.uuid for x in kwargs.get('products')]

        obj = cls(**kwargs)
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

    _memcache_fields = ['resource_url', 'shopify_id']

    def __init__(self, *args, **kwargs):
        self._memcache_key = kwargs['uuid'] if 'uuid' in kwargs else None
        super(Product, self).__init__(*args, **kwargs)

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
               client=None, resource_url='', type='', collections=None):
        """Creates a product in the datastore.
           Accepts datastore fields, returns Product object.
        """
        if not client:
            raise AttributeError("Must have client")
        if images == None:
            images = []
        if tags == None:
            tags = []

        # set uuid to its most "useful" hash.
        uu_format = "%s-%s" % (client.domain, title)
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
                          collections=collections or [])
        product.resource_url = resource_url # apparently had to be separate
        product.put()
        return product

    @staticmethod
    def get_or_create(title, description='', images=None, tags=None, price=0.0,
                      client=None, resource_url='', type=''):
        if images == None:
            images = []
        if tags == None:
            tags = []

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

        (url, www_url) = get_url_variants(url, keep_path=True)

        data = memcache.get(cls._get_memcache_key(url))
        if data:
            return db.model_from_protobuf(entity_pb.EntityProto(data))

        data = memcache.get(cls._get_memcache_key(www_url))
        if data:
            return db.model_from_protobuf(entity_pb.EntityProto(data))

        data = memcache.get(url)
        if data:
            return db.model_from_protobuf(entity_pb.EntityProto(data))

        data = memcache.get(www_url)
        if data:
            return db.model_from_protobuf(entity_pb.EntityProto(data))

        product = cls.all().filter('resource_url IN', [url, www_url]).get()
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
