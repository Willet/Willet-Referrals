import logging
import datetime
from google.appengine.ext import db
from apps.reengage.models import ReEngageQueue
from apps.reengage.social_networks import Facebook, SocialNetwork
from util.urihandler import URIHandler

POST_CLASSES = {
    "facebook": Facebook,
}

class ReEngageCron(URIHandler):
    def get(self):
        self.post()

    # TODO: This probably needs to use task queues...
    # TODO: How to make scheduling more flexible
    def post(self):
        today = datetime.datetime.today()
        if today.isoweekday() not in xrange(1,6):
            logging.info("Not a weekday; skipping.")
            return

        queues = ReEngageQueue.all()
        for queue in queues:
            logging.info("Sending content for %s..." % queue)
            logging.info("Queued: %s" % queue.queued)
            if not queue.queued:
                continue

            products = queue.get_products()
            logging.info("Products: %s" % products)
            if not products:
                logging.info("No products!")
                continue

            post_key = queue.queued[0]

            try:
                post = db.get(post_key)
                cls  = POST_CLASSES.get(post.network, SocialNetwork)

                logging.info("Preparing post...")
                for product in products:
                    logging.info("Sending content for %s..." % product)
                    cls.post(post, product=product)

            except Exception, e:
                logging.error(e)
                continue # Don't continue...

            logging.info("Post: %s" % post_key)

            queue.expired.append(post_key)
            queue.queued.remove(post_key)
            queue.put()
