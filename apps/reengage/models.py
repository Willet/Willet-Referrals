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
from apps.product.models import Product
from apps.user.models import User

from util.consts import REROUTE_EMAIL, SHOPIFY_APPS, APP_DOMAIN, URL
from util.helpers import to_dict, generate_uuid, url
from util.model import Model

class ReEngage(App):
    def __init__(self, *args, **kwargs):
        """ Initialize this model """
        super(ReEngage, self).__init__(*args, **kwargs)

    def _validate_self(self):
        return True


class ReEngageShopify(ReEngage, AppShopify):
    """use .queue to get the app's main queue, and
           .queues to get a list of queues associated with this app
    """
    fb_app_id = db.StringProperty()
    fb_secret = db.StringProperty()

    def __init__(self, *args, **kwargs):
        """ Initialize this model """
        super(ReEngageShopify, self).__init__(*args, **kwargs)

    def _validate_self(self):
        return True

    def do_install(self):
        """ Install ReEngage scripts and webhooks for this store """
        app_name = self.__class__.__name__

        # Create cohort for asset
        cohort_id = ReEngageCohortID.get_latest()

        # TODO: We should use 'product_hooks_too', and then our hooks should
        # only create a queue if one doesn't exist.
        self.queue_webhooks(webhooks=[{
            "webhook": {
                    "address": "%s/r/shopify/webhook/product/create" % (URL),
                    "format": "json", "topic": "products/create"
                }
            }, {
                "webhook": {
                    "address": "%s/r/shopify/webhook/product/update" % (URL),
                    "format": "json", "topic": "products/update"
                }
            }, {
                "webhook": {
                    "address": "%s/r/shopify/webhook/product/delete" % (URL),
                    "format": "json", "topic": "products/delete"
                }
            }, {
                "webhook": {
                    "address": "%s/r/shopify/webhook/collections/create" % (URL),
                    "format": "json", "topic": "collections/create"
                }
            }, {
                "webhook": {
                    "address": "%s/r/shopify/webhook/collections/update" % (URL),
                    "format": "json", "topic": "collections/update"
                }
            }, {
                "webhook": {
                    "address": "%s/r/shopify/webhook/collections/delete" % (URL),
                    "format": "json", "topic": "collections/delete"
                }
            }
        ])

        self.queue_script_tags(script_tags=[{
            "script_tag": {
                "src": "%s/r/shopify/load/reengage-buttons.js" % URL,
                "event": "onload"
            }
        }])
        self.queue_assets(assets=[{
            'asset': {
                'key': 'snippets/leadspeaker-fb-id.liquid',
                'value': """
                    <meta property="fb:app_id" content="%s">
                """ % (self.fb_app_id)
            }
        }, {
            'asset': {
                'key': 'snippets/leadspeaker-canonical-url.liquid',
                'value': """
                    <link rel="canonical" href="{{ canonical_url | downcase }}/%s" />
                    <meta property="og:url" content="{{ canonical_url | downcase }}/%s" />
                """ % (cohort_id.uuid, cohort_id.uuid)
            }
        }, {
            'asset': {
                'key': 'snippets/leadspeaker-header.liquid',
                'value': """

                      {% if template contains 'product' %}
                          {% include 'leadspeaker-canonical-url' %}
                      {% else %}
                          <link rel="canonical" href="{{ canonical_url | downcase }}" />
                          <meta property="og:url" content="{{ canonical_url | downcase }}" />
                      {% endif %}
                      {% include 'leadspeaker-fb-id' %}
                      <meta property="og:type" content="product">
                      <meta property="og:site_name" content="{{ shop.name | escape }}" />

                      {% if template == 'index' %}
                       <title>{{ shop.name }}</title>
                       <meta property="og:title" content="{{ shop.name }}" />
                      {% elsif template == '404' %}
                        <title>Page Not Found | {{ shop.name | escape }}</title>
                        <meta property="og:title" content="Page not found" />
                      {% else %}
                       <title>{{ page_title }} | {{ shop.name | escape }}</title>
                       <meta property="og:title" content="{{ page_title }}" />
                      {% endif %}

                      {% assign maxmeta = 155 %}
                      {% if template contains 'product' %}
                      <meta name="description" content="{{ product.description | strip_html | strip_newlines | truncate: maxmeta | escape }}" />
                      <meta property="og:description" content="{{ product.description | strip_html | strip_newlines | truncate: maxmeta | escape }}" />
                      {% elsif template contains 'page' %}
                      <meta name="description" content="{{ page.content | strip_html | strip_newlines | truncate: maxmeta | escape }}" />
                      <meta property="og:description" content="{{ page.content | strip_html | strip_newlines | truncate: maxmeta | escape }}" />
                      {% elsif template == 'index' and shop.description != '' %}
                      <meta name="description" content="{{ shop.description | strip_html | strip_newlines | truncate: maxmeta | escape }}" />
                      <meta property="og:description" content="{{ shop.description | strip_html | strip_newlines | truncate: maxmeta | escape }}" />
                      {% endif %}


                      {% comment %}
                        Open Graph tags for Facebook Like buttons
                      {% endcomment %}
                      {% if template contains 'product' %}
                        <meta property="og:image" content="{{ product.featured_image | product_img_url: 'original' }}" />
                      {% else %}
                        {% if settings.logo_image == "logo.png" %}
                          <meta property="og:image" content="{{ 'logo.png' | asset_url }}" />
                        {% endif %}
                      {% endif %}
                    """
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
            Email.welcomeClient("SecondFunnel LeadSpeaker", email, name, store,
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

    def update_canonical_url_snippet(self, cohort_id):
        self.queue_assets(assets=[{
            'asset': {
                'key': 'snippets/leadspeaker-canonical-url.liquid',
                'value': """
                    <link rel="canonical" href="{{ canonical_url | downcase }}/%s" />
                    <meta property="og:url" content="{{ canonical_url | downcase }}/%s" />
                """ % (cohort_id, cohort_id)
            }
        }])

        self.install_queued()

    def update_fb_app_id_snippet(self):
        self.queue_assets(assets=[{
            'asset': {
                'key': 'snippets/leadspeaker-fb-id.liquid',
                'value': """
                    <meta property="fb:app_id" content="%s">
                """ % (self.fb_app_id)
            }
        }])

        self.install_queued()


    @classmethod
    def create_app(cls, client, app_token):
        """ Constructor """
        uuid = generate_uuid(16)
        app = cls(key_name=uuid,
                  uuid=uuid,
                  client=client,
                  store_name=client.name,  # Store name
                  store_url=client.url,  # Store url
                  store_id=client.id,  # Store id
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

    def _get_own_queue(self):
        """get the app's main queue."""
        return ReEngageQueue.get_by_app_and_name(
            self, "%s-%s-%s" % ('ReEngageQueue', self.__class__.__name__,
                                self.uuid))
    # turn into attribute
    queue = property(_get_own_queue)


class ReEngageQueue(Model):
    """Represents a queue within ReEngage"""
    app_    = db.ReferenceProperty(App, collection_name='queues')
    cohorts = db.ListProperty(unicode, indexed=False)
    name    = db.StringProperty(indexed=True)

    # queued[ posts]
    queued = db.ListProperty(unicode, indexed=False)
    # expired[ posts]
    expired = db.ListProperty(unicode, indexed=False)

    # use get_products() to get a total list of products.
    collection_uuids = db.ListProperty(unicode, indexed=True)
    product_uuids = db.ListProperty(unicode, indexed=True)

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

    def to_obj(self, app_uuid=None):
        """Convert a queue into a serializable object.

        Mostly used as a preliminary step to convert to JSON
        """
        #self._remove_expired()

        posts = []
        for uuid in self.queued:
            try:
                posts.append(to_dict(ReEngagePost.get(uuid)))
            except:
                continue

        return {
            "key": "queues",
            "value": {
                "uuid"         : self.uuid,
                "app"          : app_uuid or self.app_.uuid,
                "activePosts"  : posts,
                "expiredPosts" : []
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
    def get_by_client_and_name(cls, client, name):
        """same as get_by_app_and_name, except with even more reads."""
        logging.debug('called get_by_client_and_name')
        try:
            for app in client.apps:
                queue = cls.get_by_app_and_name(app, name)
                if queue:
                    return queue
        except Exception, err:
            logging.error('%s' % err, exc_info=True)
        return None

    def get_cohorts(self, include_inactive=False):
        # Returns a list of associated cohorts
        cohorts = ReEngageCohort.all().filter("queue =", self)

        if not include_inactive:
            cohorts.filter("active =", True)

        # What do we expect is the longest a campaign will run?
        result = cohorts.fetch(limit=100)

        return result

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
        name = "%s-%s-%s" % (cls.__name__, app.__class__.__name__, app.uuid)

        queue = cls(
            uuid = uuid,
            app_ = app,
            name = name,
        )
        queue.put()

        return (queue, True)

    @classmethod
    def create(cls, **kwargs):
        """Simple wrapper around init."""
        logging.debug('called %r.create' % cls.__name__)
        kwargs['uuid'] = kwargs.get('uuid', generate_uuid(16))
        queue = cls(**kwargs)
        queue.put()
        return queue

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


class ReEngageCohortID(Model):
    """Represents the identifier string assigned to a weekly cohort.
    """
    created = db.DateTimeProperty(auto_now=True)

    def __init__(self, *args, **kwargs):
        """ Initialize this model """
        self._memcache_key = kwargs['uuid'] if 'uuid' in kwargs else None
        super(ReEngageCohortID, self).__init__(*args, **kwargs)

    def _validate_self(self):
        return True

    @classmethod
    def get_latest(cls):
        latest = cls.all().order("-created").get()

        if not latest:
            latest = cls.create()

        return latest

    @classmethod
    def create(cls):
        uuid = generate_uuid(16)
        obj = cls(uuid=uuid, key_name=uuid)
        obj.put()
        return obj


class ReEngageCohort(Model):
    """Represents a queue/cohort association within ReEngage"""
    queue         = db.ReferenceProperty(Model, collection_name='cohort')
    cohort_id     = db.ReferenceProperty(Model, collection_name='cohorts')
    message_index = db.IntegerProperty(default=0)
    active        = db.BooleanProperty(default=True, indexed=True)
    completed     = db.DateTimeProperty()

    def __init__(self, *args, **kwargs):
        """ Initialize this model """
        self._memcache_key = kwargs['uuid'] if 'uuid' in kwargs else None
        super(ReEngageCohort, self).__init__(*args, **kwargs)

    def _validate_self(self):
        return True

    @classmethod
    def create(cls, queue, cohort_id=None):
        uuid = generate_uuid(16)
        obj = cls(uuid=uuid, key_name=uuid, queue=queue, cohort_id=cohort_id)
        obj.put()
        return obj
