import logging
import datetime
from google.appengine.ext import db
from apps.app.models import App
from apps.app.shopify.models import AppShopify
from django.utils import simplejson as json
from apps.email.models import Email
from util.consts import REROUTE_EMAIL, SHOPIFY_APPS
from util.helpers import to_dict, generate_uuid
from util.model import Model

#TODO: How to automatically remove keys that no longer have models?

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

class ReEngageShopify(App, AppShopify):
    def __init__(self, *args, **kwargs):
        """ Initialize this model """
        super(ReEngageShopify, self).__init__(*args, **kwargs)

    def _validate_self(self):
        return True

    @classmethod
    def get_by_uuid( cls, uuid ):
        return cls.all().filter( 'uuid =', uuid ).get()

    def do_install(self):
        """ Install ReEngage scripts and webhooks for this store """
        app_name = self.__class__.__name__

        # Install yourself in the Shopify store
        self.queue_webhooks(product_hooks_too=False)
        #self.queue_script_tags(script_tags=tags)
        #self.queue_assets(assets=assets)
        self.install_queued()

        email = self.client.email or u''  # what sane function returns None?
        name  = self.client.merchant.get_full_name()
        store = self.client.name
        use_full_name = False

        if REROUTE_EMAIL:
            Email.welcomeFraser(app_name="ReEngageShopify",
                                to_addr=email,
                                name=name,
                                store_name=store,
                                store_url=self.store_url)
        else:
            # Fire off "personal" email from Fraser
            Email.welcomeClient("ReEngageShopify", email, name, store,
                                use_full_name=use_full_name)

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

    # Constructors ------------------------------------------------------------
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

    # 'Retreive or Construct'ers ----------------------------------------------
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

        elif token != None and token != '':
            if app.store_token != token:
                # TOKEN mis match, this might be a re-install
                logging.warn(
                    'We are going to reinstall this app because the stored\
                     token does not match the request token\n%s vs %s' % (
                        app.store_token,
                        token
                        )
                )
                try:
                    app.store_token = token
                    app.client = client
                    app.old_client = None
                    app.created = datetime.utcnow()
                    app.put()

                    app.do_install()
                    created = True
                except:
                    logging.error('encountered error with reinstall', exc_info=True)
        return app, created


class ReEngageQueue(Model):
    """Represents a queue within ReEngage"""
    owner    = db.ReferenceProperty(db.Model, collection_name='app')
    queued   = db.ListProperty(db.Key)
    expired  = db.ListProperty(db.Key)

    def __init__(self, *args, **kwargs):
        """ Initialize this model """
        self._memcache_key = kwargs['uuid'] if 'uuid' in kwargs else None
        super(ReEngageQueue, self).__init__(*args, **kwargs)

    def prepend(self, obj):
        """Puts a post at the front of the list"""
        self.queued.insert(0, obj.key())
        self.put()

    def append(self, obj):
        """Puts a post at the end of the list"""
        self.queued.append(obj.key())
        self.put()

    def remove_all(self):
        """Remove all posts from a queue"""
        for post in self.queued:
            db.get(post).delete()

        self.queued = []
        self.put()

    def to_json(self):
        objects = []
        expired = []

        # TODO: Refactor into cleanup method?
        for obj in self.queued:
            model_object = db.get(obj)
            if model_object:
                objects.append(to_dict(model_object))
            else:
                # Object from Key no longer exists
                expired.append(obj)

        # Remove any expired objects
        for obj in expired:
            self.queued.remove(obj)

        self.put()

        return json.dumps(objects)

    @classmethod
    def get_by_url(cls, url):
        """Find a queue based on the store url"""

        logging.info("Store URL: %s" % url)
        app   = ReEngageShopify.get_by_url(url)
        logging.info("Store App: %s" % app)
        logging.info("App UUID: %s" % app.uuid)
        queue = None
        logging.info("App Queue: %s" % queue)
        if app:
            queue = cls.all().filter("owner = ", app).get()
        logging.info("App Queue: %s" % queue)
        return queue

    @classmethod
    def get_or_create(cls, app):
        logging.info("App: %s" % app)
        logging.info("App URL: %s" % app.store_url)
        queue = cls.get_by_url(app.store_url)
        logging.info("Queue: %s" % queue)

        if queue:
            return queue, False

        uuid = generate_uuid(16)
        queue = cls(uuid=uuid, owner=app)
        queue.put()

        return queue, True

    def _validate_self(self):
        return True


class ReEngagePost(Model):
    """Represents an individual piece of content in the queue"""
    # TODO: Some unique identifier?
    network = db.StringProperty()
    content = db.StringProperty()

    def __init__(self, *args, **kwargs):
        """ Initialize this model """
        self._memcache_key = kwargs['uuid'] if 'uuid' in kwargs else None
        super(ReEngagePost, self).__init__(*args, **kwargs)

    def _validate_self(self):
        return True

    def to_json(self):
        return json.dumps(to_dict(self))