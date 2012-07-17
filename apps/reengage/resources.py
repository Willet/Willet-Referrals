import logging
from apps.reengage.models import ReEngagePost, ReEngageShopify, ReEngageQueue
from apps.reengage.social_networks import Facebook
from util.gaesessions import get_current_session
from util.helpers import generate_uuid, url as build_url
from util.urihandler import URIHandler

#TODO: Error handling
#TODO: It is stupid duplicating logic between JSON and non-JSON handlers. Fix this

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

def get_queue():
    """Obtains a queue using the provided shop url"""
    session = get_current_session()
    store_url = session.get("shop")
    if not store_url:
        return None

    app = ReEngageShopify.get_by_url(store_url)
    if not app:
        return None

    queue, created = ReEngageQueue.get_or_create(app)
    return queue


def get_post(uuid):
    """Obtains a post via the given uuid"""
    if not uuid:
        return None

    post = ReEngagePost.all().filter(" uuid = ", uuid).get()
    return post

class ReEngageQueueJSONHandler(URIHandler):
    """A resource for accessing queues using JSON"""
    @session_active
    def get(self):
        """Get all queued elements for a shop"""
        """Unless a queue_uuid is found, in which case it will be used. You'll still need to be logged in, though"""

        queue = ReEngageQueue.get(self.request.get('queue_uuid'))
        if not queue:
            session = get_current_session()
            queue = get_queue()
        if not queue:
            logging.error("Could not find queue. Store URL: %s" %
                          session.get("shop"))
            self.error(404)
            return

        response = queue.to_obj()
        self.respondJSON(response.get("value"), response.get("key"))

    @session_active
    def post(self):
        """Create a new post element in the queue"""
        session = get_current_session()

        queue = get_queue()
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
                            network=Facebook.__class__.__name__,
                            uuid=generate_uuid(16))
        post.put()

        if method == "append":
            queue.append(post)
        else:
            queue.prepend(post)

        response = queue.to_obj()
        self.respondJSON(response.get("value"), response.get("key"))

    @session_active
    def delete(self):
        """Delete all post elements in this queue"""
        session = get_current_session()

        queue = get_queue()
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
        session = get_current_session()

        #TODO: Replace with HTML view
        page = self.render_page('queue.html', {
            "t": session.get("t"),
            "shop": session.get("shop"),
            "host" : self.request.host_url
        })
        self.response.out.write(page)

    @session_active
    def post(self):
        """Create a new post element in the queue"""
        session = get_current_session()

        queue = get_queue()
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
                            network="facebook",
                            uuid=generate_uuid(16))
        post.put()

        if method == "prepend":
            queue.prepend(post)
        else:
            queue.append(post)

        response = queue.to_obj()
        self.respondJSON(response.get("value"), response.get("key"))

    @session_active
    def delete(self):
        """Delete all post elements in this queue"""
        session = get_current_session()

        queue = get_queue()
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
        self.respondJSON(response.get("value"), response.get("key"))

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
        page = self.render_page('post.html', {})
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
        self.respondJSON(data, "reach")

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
        page = self.render_page('product.html', {})
        self.response.out.write(page)

    @session_active
    def post(self):
        """Posts to the ProductSource."""
        self.error(204)
