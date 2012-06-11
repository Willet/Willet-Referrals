#!/usr/bin/python

"""File containing the SIBT class and its instance classes."""

__author__ = "Willet, Inc."
__copyright__ = "Copyright 2012, Willet, Inc"

import logging
import random

from datetime import timedelta

from google.appengine.ext import db
from google.appengine.api import memcache
from google.appengine.datastore import entity_pb

from apps.action.models import Action
from apps.app.models import App
from apps.client.models import Client
from apps.email.models import Email
from apps.gae_bingo.gae_bingo import bingo
from apps.link.models import Link
from apps.product.models import Product
from apps.product.shopify.models import ProductShopify
from apps.sibt.actions import SIBTClickAction, SIBTInstanceCreated
from apps.user.models import User
from apps.vote.models import VoteCounter

from util.consts import USING_DEV_SERVER
from util.helpers import generate_uuid, get_target_url
from util.shopify_helpers import get_url_variants
from util.model import Model
from util.memcache_ref_prop import MemcacheReferenceProperty

NUM_VOTE_SHARDS = 15


class SIBT(App):
    """Model storing the data for a client's 'Should I Buy This?' app."""

    # if the button is enabled for this app
    button_enabled = db.BooleanProperty(default=True)

    # if the top bar is enabled for this app
    top_bar_enabled = db.BooleanProperty(default=False)

    # if the bottom popup is enabled for this app
    # "default behaviour: show every 5 product pages"
    bottom_popup_enabled = db.BooleanProperty(default=True)

    # if incentivized asks is enabled
    incentive_enabled = db.BooleanProperty(default=False)

    # number of times a user has to view the page before
    # we show the top bar
    num_shows_before_tb = db.IntegerProperty(default=1)

    # Name of the store - used here for caching purposes.
    store_name = db.StringProperty(indexed=True)

    # Apps cannot be memcached by secondary key, because they are all stored
    # as App objects, and this may cause field collision.
    _memcache_fields = []

    def __init__(self, *args, **kwargs):
        """ Initialize this model """
        super(SIBT, self).__init__(*args, **kwargs)

    @classmethod
    def get_by_store_url(cls, url):
        app = None
        www_url = url

        if not url:
            return None  # can't get by store_url if no URL given

        (url, www_url) = get_url_variants(url, keep_path=False)

        app = cls.get(url)
        if app:
            return app

        # "first get by url, then by www_url"
        app = cls.all().filter('store_url IN', [url, www_url]).get()
        if not app:
            # no app in DB by store_url; try again with extra_url
            app = cls.all().filter('extra_url IN', [url, www_url]).get()
        return app

    @staticmethod
    def create(client, token):
        uuid = generate_uuid(16)
        logging.debug("creating SIBT v%s" % App.CURRENT_INSTALL_VERSION)
        app = SIBT(key_name=uuid,
                   uuid=uuid,
                   client=client,
                   store_name=client.name,  # Store name
                   store_url=client.url,
                   version=App.CURRENT_INSTALL_VERSION)

        try:
            app.store_id = client.id  # Store id
        except AttributeError:  # non-Shopify Shops need not Shop ID
            logging.warn('Store created without store_id '
                         '(ok if not installing SIBT for Shopify)')
            pass

        app.put()
        # app.do_install()  # this is JS-based; there is nothing to install
        return app

    @staticmethod
    def get_or_create(client=None, domain=''):
        """Creates a SIBT app (used like a profile) for a specific domain."""
        if client and not domain:
            domain = client.url

        if not domain:
            raise AttributeError('A valid (client or domain) '
                                 'must be supplied to create a SIBT app')

        if not client:
            client = Client.get_or_create(url=domain, email='')

        app = SIBT.get_by_store_url(domain)
        if not app:
            logging.debug("app not found; creating one.")
            app = SIBT.create(client, domain)

        if not app.store_url:
            app.store_url = domain
            app.put()

        logging.debug("SIBT::get_or_create.app is now %s" % app)
        return app

    def _validate_self(self):
        return True

    def handleLinkClick(self, urihandler, link):
        logging.info("SIBTAPP HANDLING LINK CLICK")

        # Fetch User by cookie
        user = User.get_or_create_by_cookie(urihandler, self)

        # Create a ClickAction
        act = SIBTClickAction.create(user, self, link)

        # Go to where the link points
        # Flag it so we know they came from the short link
        urihandler.redirect('%s#code=%s' % (link.target_url,
                                            link.willt_url_code))

    def create_instance(self, user, end, link, dialog="", img="",
                        motivation=None, sharing_message="", products=None):
        """SIBT2: products supersedes img."""
        logging.info("Making a SIBT instance (dialog = %s)" % dialog)
        # Make the properties
        uuid = generate_uuid(16)

        if products:
            try:
                img = products[0].images[0]
            except:
                pass

        if not img:
            img = "http://rf.rs/static/imgs/noimage-willet.png"

        # Now, make the object
        instance = SIBTInstance(key_name=uuid,
                                uuid=uuid,
                                asker=user,
                                app_=self,
                                link=link,
                                product_img=img,
                                products=products,
                                motivation=motivation,
                                sharing_message=sharing_message,
                                url=link.target_url)
        # set end if None
        if end == None:
            six_hours = timedelta(hours=6)
            end = instance.created + six_hours
        instance.end_datetime = end
        logging.info('instance created: %s\nends: %s' % (instance.created,
                                                         instance.end_datetime))
        instance.put()

        # Now, make an action
        SIBTInstanceCreated.create(user, instance=instance, medium=dialog)

        # "if it is a non-admin share on live server"
        if not user.is_admin() and not USING_DEV_SERVER:
            try:
                Email.emailDevTeam("""
                    SIBT INSTANCE:<br />
                    dialog = %s <br />
                    uuid= %s<br />
                    user.key= %s<br />
                    page= %s<br />
                    link= http://rf.rs/%s<br />
                    name= %s<br />
                    fb_uuid= %s<br />
                    fb_access_token= %s <br />
                    <a href='https://graph.facebook.com/%s?access_token=%s'>FB Profile</a>
                    """ % (
                        dialog,
                        uuid,
                        user.key(),
                        link.target_url,
                        link.willt_url_code,
                        user.get_full_name(),
                        user.get_attr('fb_identity'),
                        user.get_attr('fb_access_token'),
                        user.get_attr('fb_identity'),
                        user.get_attr('fb_access_token')
                    ),
                    subject='SIBT instance created'
                )
            except Exception, err:
               Email.emailDevTeam('SIBT INSTANCE: error printing data: '
                                  '%s' % unicode(err),
                                  subject='SIBT instance create failed')
        return instance


class SIBTInstance(Model):
    """Class definition for SIBT "Instances".

    A SIBT Instance is an encapsulated event class that stores the state of a
    given use of SIBT - chiefly created when a user creates a product vote.
    """
    # the users motivation for sharing (unknown use / deprecated)
    motivation = db.StringProperty(default="")

    # records the message with which this instance was shared.
    # if FBNoConnect (i.e. we can't capture the message),
    # then this property is empty.
    # sharing_message cannot exceed 1000 characters.
    sharing_message = db.StringProperty(required=False, default="")

    # Datetime when this model was put into the DB
    created = db.DateTimeProperty(auto_now_add=True)

    # The User who asked SIBT to their friends?
    asker = MemcacheReferenceProperty(db.Model,
                                      collection_name='sibt_instances')

    # Parent App that "owns" these instances
    app_ = db.ReferenceProperty(db.Model, collection_name="instances")

    # The Link for this instance (1 per instance)
    link = db.ReferenceProperty(db.Model, collection_name="sibt_instance")

    # URL of the Link (here for quick filter)
    url = db.LinkProperty(indexed=True)

    # URL of the product image (deprecated v11+)
    product_img = db.LinkProperty(required=False,
                                  default="http://rf.rs/static/imgs/noimage-willet.png",
                                  indexed=False)

    # use self.get_products() to get products as objects
    products = db.StringListProperty(db.Text, indexed=True)

    # Datetime when this instance should shut down and email asker
    end_datetime = db.DateTimeProperty()

    # True iff end_datetime < now. False, otherwise.
    is_live = db.BooleanProperty(default=True)

    def __init__(self, *args, **kwargs):
        """ Initialize this model """
        self._memcache_key = kwargs['uuid']
        super(SIBTInstance, self).__init__(*args, **kwargs)

    def _validate_self(self):
        if len(self.sharing_message) > 1000:
            raise ValueError('Sharing message is too long')
        return True

    @staticmethod
    def _get_from_datastore(uuid):
        return db.Query(SIBTInstance).filter('uuid =', uuid).get()

    def get_products(self):
        """Returns this instance's products as objects."""
        return [Product.get(product_uuid) for product_uuid in self.products]

    def get_winning_products(self):
        """Returns an array of products with the most votes in the instance.

        Array returned can be of one item.
        """
        instance_product_votes = []

        if not self.products:
            logging.warn("this instance has no products!")
            return []

        for product_uuid in self.products:
            product_votes = Action.all()\
                                  .filter('sibt_instance =', self)\
                                  .filter('product_uuid =', product_uuid)\
                                  .count()  # get vote counts for each product
            # [votes, votes, votes]
            instance_product_votes.append(product_votes)
        logging.debug("instance_product_votes = %r" % instance_product_votes)

        if not instance_product_votes:
            logging.warn("none of the products have votes!")
            return []

        # mash the list into a dict: {uuid: votes, uuid: votes, uuid: votes}
        instance_product_dict = dict(zip(self.products, instance_product_votes))
        logging.debug("instance_product_dict = %r" % instance_product_dict)

        if instance_product_votes.count(max(instance_product_votes)) > 1:
            # that is, if multiple items have the same score
            winning_products_uuids = filter(lambda x: instance_product_dict[x] == instance_product_votes[0],
                                            self.products)
            return Product.all()\
                          .filter('uuid IN', winning_products_uuids)\
                          .fetch(1000)
        else:
            # that is, if one product is winning the voting
            winning_product_uuid = self.products[instance_product_votes.index(max(instance_product_votes))]
            return [Product.get(winning_product_uuid)]

    # Accessor ----------------------------------------------------------------
    @staticmethod
    def get_by_asker_for_url(user, url, only_live=True):
        """Retrieve an instance by its user object and link URL (not model).

        User cannot be None.
        url cannot be ''.
        """
        if not (user and url):
            logging.error('Must supply user and url to get_by_asker_for_url!')
            return None

        data = memcache.get('%s-%s' % (user.uuid, url))
        if data:
            instance = db.model_from_protobuf(entity_pb.EntityProto(data))
        else:
            instance = SIBTInstance.all()\
                .filter('is_live =', only_live)\
                .filter('asker =', user)\
                .filter('url =', db.Link(url))\
                .get()
            if instance:
                instance._memcache()
        return instance

    @staticmethod
    def get_by_link(link, only_live=True):
        """Retrieve an instance by its associated link object."""
        return SIBTInstance.all()\
                .filter('is_live =', only_live)\
                .filter('link =', link)\
                .get()

    @staticmethod
    def get_by_uuid(uuid):
        return SIBTInstance.get(uuid)

    def get_votes_count(self):
        """Count this instance's total number of votes."""
        total = self.get_yesses_count() + self.get_nos_count()
        return total

    def get_yesses_count(self):
        """Count this instance's yes count."""
        total = memcache.get(self.uuid+"VoteCounter_yesses")
        if total is None:
            total = 0
            for counter in VoteCounter.all().\
            filter('instance_uuid =', self.uuid).fetch(NUM_VOTE_SHARDS):
                total += counter.yesses
            memcache.add(key=self.uuid+"VoteCounter_yesses", value=total)

        return total

    def get_nos_count(self):
        """Count this instance's no count."""
        total = memcache.get(self.uuid+"VoteCounter_nos")
        if total is None:
            total = 0
            for counter in VoteCounter.all().\
            filter('instance_uuid =', self.uuid).fetch(NUM_VOTE_SHARDS):
                total += counter.nos
            memcache.add(key=self.uuid+"VoteCounter_nos", value=total)

        return total

    def increment_yesses(self):
        """Increment this instance's votes (yes) counter."""
        def txn():
            index = random.randint(0, NUM_VOTE_SHARDS-1)
            shard_name = self.uuid + str(index)
            counter = VoteCounter.get_by_key_name(shard_name)
            if counter is None:
                counter = VoteCounter(key_name=shard_name,
                                      instance_uuid=self.uuid)
            counter.yesses += 1
            counter.put()

        db.run_in_transaction(txn)
        memcache.incr(self.uuid+"VoteCounter_yesses")

    def increment_nos(self):
        """Increment this instance's votes (no) counter"""
        def txn():
            index = random.randint(0, NUM_VOTE_SHARDS-1)
            shard_name = self.uuid + str(index)
            counter = VoteCounter.get_by_key_name(shard_name)
            if counter is None:
                counter = VoteCounter(key_name=shard_name,
                                      instance_uuid=self.uuid)
            counter.nos += 1
            counter.put()

        db.run_in_transaction(txn)
        memcache.incr(self.uuid+"VoteCounter_nos")


class PartialSIBTInstance(Model):
    """http://goo.gl/SWi1P

    Whenever someone doesn't FB connect, we start a PartialInstance and open up
    a FB dialog. We don't know if they actually pushed the message to FB or not,
    right? This is why it's only a Partial Instance. When the User is redirected
    to our "Thanks" screen, we complete the partialinstance and make a full one
    and delete the partial one. If the person cancels, the PartialInstance is
    deleted. If the person closes the window, the PartialInstance stays, but
    ... "expires".

    Each User can have at most 1 PartialInstance.
    """
    # User is the only index.
    user = MemcacheReferenceProperty(db.Model,
                                     collection_name='partial_sibt_instances',
                                     indexed=True)
    link = db.ReferenceProperty(db.Model,
                                collection_name='link_partial_sibt_instances',
                                indexed=False)
    # deprecated (SIBT now should accept 2 or more products)
    product = db.ReferenceProperty(db.Model,
                                   collection_name='product_partial_sibt_instances',
                                   indexed=False)

    # use self.get_products() to get products as objects
    products = db.StringListProperty(db.Text, indexed=True)

    app_ = db.ReferenceProperty(db.Model,
                                collection_name='app_partial_sibt_instances',
                                indexed=False)

    def __init__(self, *args, **kwargs):
        """ Initialize this model """
        self._memcache_key = kwargs['uuid']
        super(PartialSIBTInstance, self).__init__(*args, **kwargs)

    @classmethod
    def _get_from_datastore(cls, uuid):
        return db.Query(cls).filter('uuid =', uuid).get()

    def _validate_self(self):
        return True

    def get_products(self):
        """Returns this instance's products as objects."""
        return [Product.get(product_uuid) for product_uuid in self.products]

    @classmethod
    def create(cls, user, app, link, product=None, products=None):
        """Users can only have 1 of these ever.

        If they already have one, update it.
        Otherwise, make a new one.
        """
        instance = cls.get_by_user(user)
        if instance:
            instance.link = link
            instance.product = product
            instance.products = products
            instance.app_ = app
        else:
            uuid = generate_uuid(16)

            instance = cls(key_name=uuid,
                           uuid=uuid,
                           user=user,
                           link=link,
                           product=product,
                           products=products,
                           app_=app)
        instance.put()
        return instance

    @classmethod
    def get_by_user(cls, user):
        return cls.all().filter('user =', user).get()


# retrieval helpers
def get_app(**kwargs):
    """Helper function for "getting apps."

    It uses the following methods, IN THIS ORDER:
    - if urihandler is supplied, then urihandler.request.get() will be used in
      addition to what you supply as kwargs manually.
    - if app_uuid is supplied, return App.
    - if store_url is supplied, return App.get_by_url(...).
    - if page_url is supplied, try to return App.get_by_url(...).
    - if client_uuid is supplied, return Client.apps[0].
      Warning! This app may or may not be the one you want.

    default: None

    """
    app = None

    urihandler = kwargs.get('urihandler', None)
    # picks either urihandler.request.get() or kwargs.get().
    # take that, circularreferenciophobes!
    req = getattr(urihandler, 'request', None) or kwargs

    app_uuid = req.get('app_uuid', '')
    if app_uuid:
        app = App.get(app_uuid)
        if app:
            return app

    store_url = req.get('store_url', '')
    logging.debug('get_app: store_url = %r' % store_url)
    if store_url:
        app = App.get_by_url(store_url)
        if app:
            return app

    page_url = req.get('page_url', '')
    if page_url:
        app = App.get_by_url(page_url)
        if app:
            return app

    client_uuid = req.get('client_uuid', '')
    client = Client.get(client_uuid)
    if client:
        app = App.get_by_client(client)
        if app:
            return app

    return app


def get_products(**kwargs):
    """Helper function for "getting products."

    It uses the following methods, IN THIS ORDER:
    - if urihandler is supplied, then urihandler.request.get() will be used in
      addition to what you supply as kwargs manually.
    - if product_uuids OR products is supplied, return a list of Products.
    - if shopify_ids is supplied, return a list of ProductShopifys.
    - if product_uuid is supplied, return [Product].
    - if shopify_id is supplied, return [ProductShopify].
    - if client_uuid and page_url are supplied, return [Product.get_or_fetch].
    - if app_uuid and page_url are supplied, return [Product.get_or_fetch].

    default: []

    These operations are NOT additive, i.e. it is not possible to use this
    type of query: product_uuid=123, shopify_id=456 -> [Product1, Product2]

    """
    products = []

    urihandler = kwargs.get('urihandler', None)
    # picks either urihandler.request.get() or kwargs.get().
    # take that, circularreferenciophobes!
    req = getattr(urihandler, 'request', None) or kwargs

    product_uuids = (req.get('products', '') or \
                     req.get('product_uuids', '')).split(',')
    if product_uuids and len(product_uuids):
        products = [Product.get(uuid) for uuid in product_uuids]
        if products[0]:
            logging.debug("get products by product_uuids, got %r" % products)
            return filter(None, products)

    shopify_ids = req.get('shopify_ids', '').split(',')
    if shopify_ids and len(shopify_ids):
        products = [ProductShopify.get_by_shopify_id(id) for id in shopify_ids]
        if products[0]:
            logging.debug("get products by shopify_ids, got %r" % products)
            return filter(None, products)

    product_uuid = req.get('product_uuid', '')
    if product_uuid:
        products = [Product.get(product_uuid)]
        if products[0]:
            logging.debug("get products by product_uuid, got %r" % products)
            return filter(None, products)

    shopify_id = req.get('shopify_id', '')
    products = [ProductShopify.get_by_shopify_id(shopify_id)]
    if products[0]:
        logging.debug("get products by shopify_id, got %r" % products)
        return filter(None, products)

    page_url = req.get('page_url', '')
    if page_url:
        client_uuid = req.get('client_uuid', '')
        client = Client.get(client_uuid)
        products = [Product.get_or_fetch(page_url, client)]
        if products[0]:
            return filter(None, products)

        app_uuid = req.get('app_uuid', '')
        app = App.get(app_uuid)
        products = [Product.get_or_fetch(page_url, app.client)]
        if products[0]:
            return filter(None, products)

    return products


def get_instance_event(**kwargs):
    """Returns an (instance, event) tuple for this pageload.

    It uses the following methods, IN THIS ORDER:
    - if urihandler is supplied, then urihandler.request.get() will be used in
      addition to what you supply as kwargs manually.
    - if instance_uuid is supplied, get it immediately.
    - if page_url is supplied, it will find an instance for the current user
      on this page.
    - if willt_code is supplied, the instance with the link of this code
      will be returned.
    - if nothing else is supplied, Actions will be scanned to see if the user
      started any instances on this page.
    - if user and app are supplied

    default: (None, '')

    """
    urihandler = kwargs.get('urihandler', None)
    # picks either urihandler.request.get() or kwargs.get().
    # take that, circularreferenciophobes!
    req = getattr(urihandler, 'request', None) or kwargs

    link = None
    target = get_target_url(req.get('url', ''))

    instance_uuid = req.get('instance_uuid')
    instance = SIBTInstance.get(instance_uuid)
    if instance:
        return (instance, 'SIBTShowingVote')

    page_url = req.get('page_url', '')
    user = get_user(urihandler=urihandler)
    instance = SIBTInstance.get_by_asker_for_url(user, page_url)
    if instance:
        return (instance, 'SIBTShowingResults')

    willet_code = req.get('willt_code')
    if willet_code:
        link = Link.get_by_code(willet_code)
        if link:
            instance = link.sibt_instance.get()
        if instance:
            return (instance, 'SIBTShowingResults')

    app = get_app(urihandler=urihandler)
    if user and app:
        instances = SIBTInstance.all(keys_only=True)\
                                .filter('url =', page_url)\
                                .fetch(100)
        key_list = [key.id_or_name() for key in instances]
        action = SIBTClickAction.get_for_instance(app, user, page_url,
                                                  key_list)
        if action:
            instance = action.sibt_instance

        if instance:
            return (instance, 'SIBTShowingVote')

        if not link:
            link = Link.all()\
                       .filter('user =', user)\
                       .filter('target_url =', target)\
                       .filter('app_ =', app)\
                       .get()
        if link:
            instance = link.sibt_instance.get()
        if instance:
            return (instance, 'SIBTShowingVote')

    if user and target:
        instance = SIBTInstance.get_by_asker_for_url(user, target)
        return (instance, 'SIBTShowingVote') # could be none

    return (None, '')


def get_user(urihandler, **kwargs):
    """Returns a User object by detecting the visitor's cookie.

    It uses the following methods, IN THIS ORDER:
    - if user_uuid is supplied, use it.
    - if cookie contains a willet_user_uuid field, we will get a user with it.
    - if cookie contains an email field, we will get a user with it.

    default: User (created by cookie)

    """
    user = None

    # picks either urihandler.request.get() or kwargs.get().
    # take that, circularreferenciophobes!
    req = getattr(urihandler, 'request', None) or kwargs

    user = User.get(req.get('user_uuid'))
    if user:
        return user

    user = User.get_by_cookie(urihandler)
    if user:
        return user

    user = User.get_by_email(req.get('email'))
    if user:
        return user

    app = get_app(urihandler=urihandler)  # None
    return User.get_or_create_by_cookie(urihandler, app)