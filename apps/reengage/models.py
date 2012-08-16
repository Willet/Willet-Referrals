#!/usr/bin/env python

import datetime
import os
import hashlib
import logging
from base64 import urlsafe_b64encode

from django.core.validators import email_re
from google.appengine.ext import db

from apps.app.models import App
from apps.app.shopify.models import AppShopify
from apps.email.models import Email
from apps.product.models import Product, ProductCollection
# from apps.reengage.shopify.models import ReEngageShopify
from apps.user.models import User

from util.consts import REROUTE_EMAIL, SHOPIFY_APPS, APP_DOMAIN, URL
from util.helpers import to_dict, generate_uuid, url
from util.model import Model

class TwitterAssociation(Model):
    #app_uuid = db.StringProperty(indexed=True)
    url      = db.StringProperty(indexed=True)
    handles  = db.StringListProperty()

    def __init__(self, *args, **kwargs):
        """ Initialize this model """
        self._memcache_key = kwargs['uuid'] if 'uuid' in kwargs else None
        super(TwitterAssociation, self).__init__(*args, **kwargs)

    def _validate_self(self):
        pass

    @classmethod
    def get_or_create(cls, url):
        result = cls.all().filter('url =', url).get()

        if result:
            return result, False

        result = cls(url=url, handles=[])
        result.put()

        return result, True


class ReEngage(App):
    def __init__(self, *args, **kwargs):
        """ Initialize this model """
        super(ReEngage, self).__init__(*args, **kwargs)

    def _validate_self(self):
        return True


class ReEngageShopify(ReEngage, AppShopify):
    def __init__(self, *args, **kwargs):
        """ Initialize this model """
        super(ReEngageShopify, self).__init__(*args, **kwargs)

    def _validate_self(self):
        return True

    def do_install(self):
        """ Install ReEngage scripts and webhooks for this store """
        app_name = self.__class__.__name__

        # Install yourself in the Shopify store
        self.queue_webhooks(product_hooks_too=True)
        self.queue_assets(assets=[{
            'asset': {
                'key': 'snippets/reengage-buttons.liquid',
                'value': """
                    {%% capture u %%}{{ canonical_url | downcase }}{%% endcapture %%}
                    {%% capture s %%}{{ shop.name | escape }}{%% endcapture %%}
                    {%% capture t %%}{%% if template == 'index' %%}{{ shop.name }}{%% elsif template == '404' %%}Page Not Found{%% else %%}{{ page_title }}{%% endif %%}{%% endcapture %%}
                    {%% capture d %%}{%% assign maxmeta = 155 %%}{%% if template contains 'product' %%}{{ product.description | strip_html | strip_newlines | truncate: maxmeta | escape | replace: '&', '%%26' }}{%% elsif template contains 'page' %%}{{ page.content | strip_html | strip_newlines | truncate: maxmeta | escape | replace: '&', '%%26' }}{%% elsif template == 'index' and shop.description != '' %%}{{ shop.description | replace: '&', '%%26' }}{%% endif %%}{%% endcapture %%}
                    {%% capture i %%}{%% if template contains 'product' %%}{{ product.featured_image | product_img_url: 'original' }}{%% elsif settings.logo_image == "logo.png" %%}{{ 'logo.png' | asset_url }}{%% endif %%}{%% endcapture %%}
                    <iframe id="_willet_buttons_iframe" src="//%s/r/url/{{u}}?buttons=1&title={{t}}&site={{s}}&image={{i}}&description={{d}}" style="height: 20px;"></iframe>
                """ % APP_DOMAIN
            }
        }])
        self.install_queued()

        email = self.client.email or u''
        name  = self.client.merchant.get_full_name()
        store = self.client.name
        use_full_name = False

        # Create a new user
        # WARNING: wrap with get_or_create
        user = ReEngageAccount(email=email, uuid=generate_uuid(16),
                               client=self.client)
        user.reset_password()

        # Get verification URL
        link = url("ReEngageVerify", qs={
            "email": email,
            "token": user.token
        })

        full_url = "https://%s%s" % (APP_DOMAIN, link)

        if REROUTE_EMAIL:
            Email.welcomeFraser(app_name="ReEngageShopify",
                                to_addr=email,
                                name=name,
                                store_name=store,
                                store_url=self.store_url)
        else:
            # Fire off "personal" email from Fraser
            Email.welcomeClient("ShopConnection Engage", email, name, store,
                                use_full_name=use_full_name,
                                additional_data={"url": full_url})

        # Email DevTeam
        Email.emailDevTeam(
            'ReEngageShopify Install: %s %s %s' % (
                self.uuid,
                self.client.name,
                self.client.url
                ),
            subject='App installed'
        )

        # Start sending email updates
        if app_name in SHOPIFY_APPS and 'mailchimp_list_id' in SHOPIFY_APPS[app_name]:
            self.client.subscribe_to_mailing_list(
                list_name=app_name,
                list_id=SHOPIFY_APPS[app_name]['mailchimp_list_id']
            )

        return

    @classmethod
    def create_app(cls, client, app_token):
        """ Constructor """
        uuid = generate_uuid(16)
        app = cls(key_name=uuid,
                  uuid=uuid,
                  client=client,
                  store_name=client.name, # Store name
                  store_url=client.url,  # Store url
                  store_id=client.id,   # Store id
                  store_token=app_token)
        app.put()

        app.do_install()

        return app

    @classmethod
    def get_or_create(cls, client, token):
        """Try to retrieve the app.  If no app, create one.

        Returns:
            app     - the created / obtained app
            created - a boolean indicating whether or not this was created now
        """
        created = False
        app = cls.get_by_url(client.url)

        if app is None:
            app = cls.create_app(client, token)
            created = True

        elif token:
            if app.store_token != token:
                # TOKEN mis match, this might be a re-install
                logging.warn(
                    'We are going to reinstall this app because the stored\
                     token does not match the request token\n%s vs %s' % \
                     (app.store_token,token)
                )
                try:
                    app.store_token = token
                    app.client = client
                    app.old_client = None
                    app.created = datetime.datetime.utcnow()
                    app.put()

                    app.do_install()
                    created = True
                except:
                    logging.error('encountered error with reinstall',
                                  exc_info=True)
        return app, created


class ReEngageQueue(Model):
    """Represents a queue within ReEngage"""
    app_ = db.ReferenceProperty(App, collection_name='queues')
    name = db.StringProperty(indexed=True)

    # queued[ posts]
    queued = db.ListProperty(unicode, indexed=False)
    # expired[ posts]
    expired = db.ListProperty(unicode, indexed=False)

    # use get_products() to get a total list of products.
    # to save time,
    collection_uuids = db.ListProperty(unicode, indexed=False)
    product_uuids = db.ListProperty(unicode, indexed=False)

    def __init__(self, *args, **kwargs):
        """ Initialize this model """
        self._memcache_key = kwargs['uuid'] if 'uuid' in kwargs else None
        super(ReEngageQueue, self).__init__(*args, **kwargs)

    def prepend(self, obj):
        """Puts a post at the front of the list"""
        if not self.queued:
            self.queued = []
        self.queued.insert(0, unicode(obj.uuid))
        logging.debug('self.queued = %r' % self.queued)
        self.put()

    def append(self, obj):
        """Puts a post at the end of the list"""
        if not self.queued:
            self.queued = []
        self.queued.append(unicode(obj.uuid))
        logging.debug('self.queued = %r' % self.queued)
        self.put()

    def remove_all(self):
        """Remove all posts from a queue"""
        logging.info("Queued items: %s" % self.queued)
        for uuid in self.queued:
            post = db.get(uuid)
            logging.info("Deleting post: %s" % post.content)
            post.delete()

        self.queued = []
        self.put()

    def _remove_expired(self):
        """Remove any objects that have been deleted"""
        expired = []
        for uuid in self.queued:
            model_object = ReEngagePost.get(uuid)
            if not model_object:
                expired.append(uuid)

        for uuid in expired:
            self.queued.remove(uuid)

        self.put()

    def to_obj(self):
        """Convert a queue into a serializable object.

        Mostly used as a preliminary step to convert to JSON
        """
        self._remove_expired()

        posts = []
        for uuid in self.queued:
            try:
                posts.append(to_dict(ReEngagePost.get(uuid)))
            except:
                continue

        expired = []
        for uuid in self.expired:
            try:
                expired.append(to_dict(ReEngagePost.get(uuid)))
            except:
                continue

        return {
            "key": "queues",
            "value": {
                "uuid"         : self.uuid,
                "app"          : self.app_.uuid,
                "activePosts"  : posts,
                "expiredPosts" : expired
            }
        }

    def get_products(self):
        """Get products associated with this queue."""
        total_product_uuids = self.product_uuids
        collections = [ProductCollection.get(x) for x in self.collection_uuids]

        # add all product uuids to the totals list.
        for collection in collections:
            col_prod_uuids = [x.uuid for x in collection.products]
            total_product_uuids.extend(col_prod_uuids)

        # unique-ify it, then return objects
        total_product_uuids = list(frozenset(total_product_uuids))
        return [Product.get(x) for x in total_product_uuids]

    def add_products(self, value):
        """given value (either a Product or ProductCollection object),
        add it to either product_uuids or collection_uuids, respectively.
        """
        if isinstance(value, Product):
            self.product_uuids.append(value.uuid)
            self.product_uuids = list(frozenset(self.product_uuids))

        elif isinstance(value, ProductCollection):
            self.collection_uuids.extend([x.uuid for x in value.products])
            self.collection_uuids = list(frozenset(self.collection_uuids))

        self.put_later()

    def clear_products(self):
        """empties product_uuids and collection_uuids."""
        self.product_uuids = []
        self.collection_uuids = []
        self.put_later()


    @classmethod
    def get_by_app_and_name(cls, app, name):
        """Find a queue based on app and name. To save space,
        this lookup is not indexed.

        default: None
        """
        queues = app.queues
        for queue in queues:
            if queue.name == name:
                return queue

    @classmethod
    def get_by_url(cls, url):
        """Find a queue based on the store url"""
        app   = ReEngageShopify.get_by_url(url)
        queue = None
        if app:
            queue = cls.all().filter("app_ = ", app).get()
        return queue

    @classmethod
    def get_or_create(cls, app):
        """Get a queue, or create one if none is associated with app."""
        queue = cls.get_by_url(app.store_url)

        if queue:
            return (queue, False)

        uuid = generate_uuid(16)
        queue = cls(uuid=uuid, app_=app)
        queue.put()

        return (queue, True)

    def _validate_self(self):
        return True


class ReEngagePost(Model):
    """Represents an individual piece of content in the queue"""
    title   = db.StringProperty(indexed=True)
    network = db.StringProperty(indexed=True)
    content = db.StringProperty(multiline=True)

    def __init__(self, *args, **kwargs):
        """ Initialize this model """
        self._memcache_key = kwargs['uuid'] if 'uuid' in kwargs else None
        super(ReEngagePost, self).__init__(*args, **kwargs)

    def _validate_self(self):
        return True

    def to_obj(self):
        """Convert a post into a serializable object.

        Mostly used as a preliminary step to convert to JSON
        """
        return {
            "key": "post",
            "value": to_dict(self)
        }


class ReEngageAccount(User):
    email    = db.EmailProperty(indexed=True)
    salt     = db.StringProperty(indexed=False)
    hash     = db.StringProperty(indexed=False)
    verified = db.BooleanProperty(default=False)

    # Used for one-time tokens
    token    = db.StringProperty(default="")
    token_exp= db.DateTimeProperty()

    def __init__(self, *args, **kwargs):
        """ Initialize this model """
        self._memcache_key = kwargs['uuid'] if 'uuid' in kwargs else None
        super(ReEngageAccount, self).__init__(*args, **kwargs)

    def _validate_self(self):
        return True

    def verify(self, password):
        """Check that a user's password is correct."""
        hash = hashlib.sha512(self.salt + password).hexdigest()
        return hash == self.hash

    def set_password(self, password):
        """Set a user's password"""
        salt = urlsafe_b64encode(os.urandom(64))
        hash = hashlib.sha512(salt + password).hexdigest()

        self.salt = salt
        self.hash = hash
        self.put()

    def reset_password(self):
        """Creates a token to allow the user to reset their password.

        User is given a token (which expires) to verify their email address
        and set a new password."""
        token = urlsafe_b64encode(os.urandom(32))

        self.hash      = ""
        self.salt      = ""
        self.verified  = False
        self.token     = token
        self.token_exp = datetime.datetime.now() + datetime.timedelta(days=1)

        self.put()

    def forgot_password(self):
        """As `reset_password` plus sends an email."""
        self.reset_password()

        # Send verification email
        Email.verify_reengage_token_email(self.email, self.token)

    @classmethod
    def get_or_create(cls, username):
        """Gets or creates a user account, if none exists"""
        logging.info("Obtaining user...")

        user = cls.all().filter('email = ', username).get()
        logging.info("User: %s" % user)

        # User already exists
        if user:
            return (user, False)

        if username and email_re.match(username):
            # Create user
            logging.info("Creating new user")
            user  = cls(email=username, uuid=generate_uuid(16))
            user.forgot_password()

            return (user, True)
        else:
            return (None, False)
