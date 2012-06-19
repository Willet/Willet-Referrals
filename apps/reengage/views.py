import logging
from django.utils import simplejson as json
from google.appengine.ext import db
from util.urihandler import URIHandler
from util.helpers import to_dict
from apps.reengage.models import *

#TODO: How to avoid stupid `if json else` construct
#TODO: How to return json response
#TODO: Error handling
#TODO: Reduce dependence on Shopify

def get_queue(request):
    store_url = request.get("shop")
    if not store_url:
        return None

    queue = ReEngageQueue.get_by_url(store_url)
    return queue

class ReEngageQueueHandler(URIHandler):
    def get(self):
        """Get all queued elements for a shop"""
        if self.is_json():
            queue = get_queue(self.request)
            if not queue:
                self.respond(400)
                return

            logging.info(queue.queued)
            objects = [to_dict(db.get(obj)) for obj in queue.queued]

            json_response = json.dumps(objects)
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

        post = ReEngagePost(content=content, network="facebook")
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
    # Unused, for now

    def get(self):
        """Get all details for a given post"""
        self.respond(200)

    def put(self):
        """Update the details of a post"""
        self.respond(200)

    def delete(self):
        """Delete an individual post"""
        self.respond(200)