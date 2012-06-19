from google.appengine.ext import db
from apps.app.models import App
from apps.app.shopify.models import AppShopify
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


class ReEngageQueue(Model):
    """Represents a queue within ReEngage"""
    app_uuid = db.ReferenceProperty(db.Model, collection_name='app')
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

    @classmethod
    def get_by_url(cls, url):
        """Find a queue based on the store url"""
        #app   = App.get_by_url(url)
        #queue = cls.all().filter("app_uuid = ", app.uuid).get()
        # TODO: Get app properly
        queue = cls.all().get()
        return queue

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