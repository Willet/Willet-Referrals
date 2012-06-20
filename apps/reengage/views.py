import logging
from django.utils import simplejson as json
from google.appengine.ext import db
from apps.client.shopify.models import ClientShopify
from util.consts import SHOPIFY_APPS
from util.urihandler import URIHandler
from util.helpers import to_dict, generate_uuid, url as build_url
from apps.reengage.models import *

#TODO: How to avoid stupid `if json else` construct`
#TODO: How to return json response
#TODO: Error handling

def get_queue(request):
    store_url = request.get("shop")
    if not store_url:
        return None

    app = ReEngageShopify.get_by_url(store_url)
    if not app:
        return None

    queue, created = ReEngageQueue.get_or_create(app)
    return queue

def get_post(uuid):
    if not uuid:
        return None

    post = ReEngagePost.all().filter(" uuid = ", uuid).get()
    return post

class ReEngageLanding(URIHandler):
    """Display the default 'welcome' page."""
    def get(self):
        template_values = {
            "SHOPIFY_API_KEY": SHOPIFY_APPS['ReEngageShopify']['api_key']
        }

        self.response.out.write(self.render_page('landing.html',
                                                 template_values))


class ReEngageWelcome(URIHandler):
    def get(self):
        token  = self.request.get( 't' )
        shop   = self.request.get("shop")
        client = ClientShopify.get_by_url(shop)

        # Fetch or create the app
        app, created = ReEngageShopify.get_or_create(client,token=token)

        # Should probably use sessions instead of query string
        page = build_url("ReEngageQueueHandler", qs={
            "t"   : app.store_token,
            "shop": app.store_url,
        })
        self.redirect(page)


class ReEngageQueueHandler(URIHandler):
    def get(self):
        """Get all queued elements for a shop"""
        if self.is_json():
            queue = get_queue(self.request)
            if not queue:
                logging.error("Could not find queue. Store URL: %s" %
                             self.request.get("shop"))
                self.respond(400)
                return

            json_response = queue.to_json()
            self.response.headers.add_header('content-type', 'application/json', charset='utf-8')
            self.response.out.write(json_response)
        else:
            page = self.render_page('index.html', {})
            self.response.out.write(page)

    def post(self):
        """Create a new post element in the queue"""
        queue = get_queue(self.request)
        if not queue:
            logging.error("Could not find queue. Store URL: %s" %
                         self.request.get("shop"))
            self.respond(400)
            return

        # TODO: Validate the arguments
        content = self.request.get("content")
        method  = self.request.get("method", "append")

        post = ReEngagePost(content=content,
                            network="facebook",
                            uuid=generate_uuid(16))
        post.put()

        if method == "append":
            queue.append(post)
        else:
            queue.prepend(post)

        self.respond(200)

    def delete(self):
        """Delete all post elements in this queue"""
        queue = get_queue(self.request)
        if not queue:
            logging.error("Could not find queue. Store URL: %s" %
                         self.request.get("shop"))
            self.respond(400)
            return

        queue.remove_all()
        self.respond(200)


class ReEngagePostHandler(URIHandler):
    def get(self, uuid):
        """Get all details for a given post"""
        post = get_post(uuid)
        if not post:
            logging.error("Could not find post. UUID: %s" % uuid)
            self.respond(400)
            return

        json_response = post.to_json()
        self.response.out.write(json_response)

    def put(self, uuid):
        """Update the details of a post"""
        # Unused, for now
        self.respond(200)

    def delete(self, uuid):
        """Delete an individual post"""
        post = get_post(uuid)
        if not post:
            logging.error("Could not find post. UUID: %s" % uuid)
            self.respond(400)
            return

        # TODO: What about Keys that reference this?
        post.delete()
        self.respond(200)