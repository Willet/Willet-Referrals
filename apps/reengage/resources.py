#!/usr/bin/env python

import logging
import webob
import cgi

from apps.client.models import Client
from apps.reengage.models import ReEngagePost, ReEngageShopify, ReEngageQueue
from apps.reengage.social_networks import Facebook

from util.consts import ADMIN_IPS, USING_DEV_SERVER
from util.gaesessions import get_current_session
from util.helpers import generate_uuid, get_list_item, url as build_url
from util.urihandler import URIHandler

def session_active(fn):
    """Decorator for checking if a session is active and a user is logged in."""
    def wrapped(*args, **kwargs):
        session = get_current_session()

        if session.is_active() and session.get("logged_in"):
            logging.info("Session is active: Allow user to access resource.")
            fn(*args, **kwargs)
        else:
            logging.info("Session is inactive: Redirect user.")
            self = args[0] # Assume that self is the first arg
            page = build_url("ReEngageLogin", qs={
                "t"   : session.get("token"),
                "shop": session.get("shop")
            })
            self.redirect(page)

    return wrapped


def get_queues(uuid=None, name=''):
    """Obtains a queue using the provided shop url.

    If a uuid is specified, returns an queue instead of a list of queues.
    If a name is specified, returns an queue instead of a list of queues.
    """
    session = get_current_session()
    store_url = session.get("shop")
    if not store_url:
        return None

    app = ReEngageShopify.get_by_url(store_url)
    if not app:
        return None

    if uuid:
        queue = ReEngageQueue.get(uuid) or None
        return queue

    if name:
        queue = ReEngageQueue.get_by_app_and_name(app=app, name=name) or None
        return queue

    queue, created = ReEngageQueue.get_or_create(app)
    return [queue]


def get_post(uuid):
    """Obtains a post via the given uuid"""
    if not uuid:
        return None

    post = ReEngagePost.all().filter(" uuid = ", uuid).get()
    return post


class ReEngageQueuesJSONHandler(URIHandler):
    """A resource for accessing queues using JSON"""
    @session_active
    def get(self):
        """Get all queued elements for a shop

        Unless a queue_uuid is found, in which case it will be used.
        You'll still need to be logged in, though.
        """
        queues = []

        client = Client.get(self.request.get('client_uuid'))
        if client:
            client_queues = [p.queue for p in client.products]
            logging.debug('adding products\' queues: %r' % client_queues)
            queues.extend(client_queues)

        app = ReEngageShopify.get(self.request.get('app_uuid'))
        if app:
            logging.debug('adding app\'s queues: %r' % app.queues)
            queues.extend(app.queues)

        if not queues:
            session = get_current_session()
            queues = get_queues()

        if not queues:
            logging.error("Could not find queue. Store URL: %s" %
                          session.get("shop"))
            self.error(404)
            return

        #
        app_uuid = None
        if app:
            app_uuid = app.uuid

        # build json response for "a bunch of queues"
        response = {'key': 'queues',
                    'value': []}
        for queue in queues:
            response['value'].append(queue.to_obj(app_uuid=app_uuid)['value'])
        self.respondJSON(response.get("value"),
                         response_key=response.get("key"))


class ReEngageQueueJSONHandler(URIHandler):
    """A resource for accessing queues using JSON"""
    @session_active
    def get(self):
        """Get all queued elements for a shop

        Unless a queue_uuid is found, in which case it will be used.
        You'll still need to be logged in, though.
        """

        queue = ReEngageQueue.get(self.request.get('queue_uuid'))
        if not queue:
            session = get_current_session()
            queues = get_queues()
            queue = get_list_item(queues, 0)

        if not queue:
            logging.error("Could not find queue. Store URL: %s" %
                          session.get("shop"))
            self.error(404)
            return

        response = queue.to_obj()
        self.respondJSON(response.get("value"),
                         response_key=response.get("key"))

    @session_active
    def post(self):
        """Create a new post element in the queue"""
        session = get_current_session()
        uuid = self.request.get('queue_uuid', '')

        queue = get_queues(uuid=uuid)
        if not queue:
            logging.error("Could not find queue. Store URL: %s" %
                          session.get("shop"))
            self.error(404)
            return

        # TODO: Validate the arguments
        title   = self.request.get("title")
        content = self.request.get("content")
        method  = self.request.get("method", "append")

        uuid = generate_uuid(16)
        post = ReEngagePost(title=title,
                            content=content,
                            network=Facebook.__name__,
                            uuid=uuid,
                            key_name=uuid)
        post.put()

        if method == "append":
            logging.debug('appending post %r to %r' % (post, queue))
            queue.append(post)
        else:
            logging.debug('prepending post %r to %r' % (post, queue))
            queue.prepend(post)

        response = post.to_obj()
        self.respondJSON(response.get("value"), response.get("key"))

    @session_active
    def delete(self):
        """Delete all post elements in this queue"""
        session = get_current_session()
        uuid = self.request.get('queue_uuid', '')

        queue = get_queues(uuid=uuid)
        if not queue:
            logging.error("Could not find queue. Store URL: %s" %
                          session.get("shop"))
            self.error(404)
            return

        queue.remove_all()
        self.error(204)


class ReEngageQueueHandler(URIHandler):
    """A resource for accessing queues using HTML"""
    @session_active
    def get(self):
        """Get all queued elements for a shop"""
        queue = None
        session = get_current_session()

        app = ReEngageShopify.get_by_url(session.get("shop"))
        # if app:
        #     queue = app.queues[0]
        queue = get_list_item(app.queues, 0)

        # if queue_uuid is specified, operate on that specific one
        queue_uuid = self.request.get('queue_uuid', '')
        if queue_uuid:
            queue = ReEngageQueue.get(queue_uuid)

        #TODO: Replace with HTML view
        page = self.render_page('reengage/queue.html', {
            'debug': USING_DEV_SERVER or (self.request.remote_addr in ADMIN_IPS),
            "t": session.get("t"),
            "shop": session.get("shop"),
            "host" : self.request.host_url,
            'queue': queue,
            'app': app
        })
        self.response.out.write(page)

    @session_active
    def post(self):
        """Create a new post element in the queue"""
        session = get_current_session()
        uuid = self.request.get('queue_uuid', '')

        queue = get_queues(uuid=uuid)
        if not queue:
            logging.error("Could not find queue. Store URL: %s" %
                         session.get("shop"))
            self.error(404)
            return

        # TODO: Validate the arguments
        title   = self.request.get("title")
        content = self.request.get("content")
        method  = self.request.get("method", "append")

        post = ReEngagePost(title=title,
                            content=content,
                            network=Facebook.__name__,
                            uuid=generate_uuid(16))
        post.put()

        if method == "prepend":
            queue.prepend(post)
        else:
            queue.append(post)

        response = queue.to_obj()
        self.respondJSON(response.get("value"),
                         response_key=response.get("key"))

    @session_active
    def delete(self):
        """Delete all post elements in this queue"""
        session = get_current_session()
        uuid = self.request.get('queue_uuid', '')

        queue = get_queues(uuid=uuid)
        if not queue:
            logging.error("Could not find queue. Store URL: %s" %
                         session.get("shop"))
            self.error(404)
            return

        queue.remove_all()
        self.error(204)


class ReEngagePostJSONHandler(URIHandler):
    """A resource for accessing posts using JSON"""
    @session_active
    def get(self, uuid):
        """Get all details for a given post"""
        post = get_post(uuid)
        if not post:
            logging.error("Could not find post. UUID: %s" % uuid)
            self.error(404)
            return

        response = post.to_obj()
        self.respondJSON(response.get("value"),
                         response_key=response.get("key"))

    @session_active
    def put(self, uuid):
        """Update the details of a post.

        check ReEngageQueueHandler.put for post creation.
        """
        # http://code.google.com/p/googleappengine/issues/detail?id=170
        params = cgi.parse_qsl(self.request.body)
        self.request.PUT = webob.MultiDict(params)
        title   = self.request.PUT.get("title")
        content = self.request.PUT.get("content")

        post = ReEngagePost.get(uuid)

        if not post:
            self.error(404)  # done
            return

        if title:
            post.title = title
        if content:
            post.content = content

        post.put()
        self.response.out.write('OK')

    @session_active
    def delete(self, uuid):
        """Delete an individual post"""
        post = get_post(uuid)
        if not post:
            logging.error("Could not find post. UUID: %s" % uuid)
            self.error(404)
            return

        # TODO: What about Keys that reference this params = urlparse.parse_qsl(self.request.body)

        post.clear_cache()
        post.delete()
        self.error(204)


class ReEngagePostHandler(URIHandler):
    """A resource for accessing posts using HTML"""
    @session_active
    def get(self, uuid):
        """Get all details for a given post"""
        post = get_post(uuid)
        if not post:
            logging.error("Could not find post. UUID: %s" % uuid)
            self.error(404)
            return

        #TODO: Replace with HTML view
        page = self.render_page('reengage/post.html', {})
        self.response.out.write(page)

    @session_active
    def put(self, uuid):
        """Update the details of a post"""
        # Unused, for now
        self.error(204)

    @session_active
    def delete(self, uuid):
        """Delete an individual post"""
        post = get_post(uuid)
        if not post:
            logging.error("Could not find post. UUID: %s" % uuid)
            self.error(404)
            return

        # TODO: What about Keys that reference this post?
        post.delete()
        self.error(204)


class ReEngageProductSourceJSONHandler(URIHandler):
    """A resource for accessing products using JSON

    A product source is any category, product, or store
    """
    @session_active
    def get(self):
        """Obtains information about a given ProductSource."""
        url = self.request.get("url")

        data = Facebook.get_reach(url)
        self.respondJSON(data, response_key="reach")

    @session_active
    def post(self):
        """Posts to the ProductSource."""
        self.error(204)


class ReEngageProductSourceHandler(URIHandler):
    """A resource for accessing products using HTML

    A product source is any category, product, or store
    """
    @session_active
    def get(self):
        """Obtains information about a given ProductSource."""
        url = self.request.get("url")

        #TODO: Replace with HTML view
        page = self.render_page('reengage/product.html', {})
        self.response.out.write(page)

    @session_active
    def post(self):
        """Posts to the ProductSource."""
        self.error(204)
