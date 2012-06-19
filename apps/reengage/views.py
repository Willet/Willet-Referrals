import logging
from django.utils import simplejson as json
from google.appengine.ext import db
from util.urihandler import URIHandler
from util.helpers import to_dict, generate_uuid
from apps.reengage.models import *

#TODO: How to avoid stupid `if json else` construct
#TODO: How to return json response
#TODO: Error handling

def get_queue(request):
    store_url = request.get("shop")
    if not store_url:
        return None

    queue = ReEngageQueue.get_by_url(store_url)
    return queue

def get_post(uuid):
    if not uuid:
        return None

    post = ReEngagePost.all().filter(" uuid = ", uuid).get()
    return post

class ReEngageQueueHandler(URIHandler):
    def get(self):
        """Get all queued elements for a shop"""
        if self.is_json():
            queue = get_queue(self.request)
            if not queue:
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
            self.respond(400)
            return

        queue.remove_all()
        self.respond(200)


class ReEngagePostHandler(URIHandler):
    def get(self, uuid):
        """Get all details for a given post"""
        post = get_post(uuid)
        if not post:
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
            self.respond(400)
            return

        # TODO: What about Keys that reference this?
        post.delete()
        self.respond(200)