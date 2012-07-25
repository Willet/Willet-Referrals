import logging
import datetime
from google.appengine.ext import db
from apps.reengage.models import ReEngageQueue, ReEngagePost
from apps.reengage.social_networks import Facebook, SocialNetwork
from util.urihandler import URIHandler

POST_CLASSES = {
    Facebook.__name__: Facebook,
}

class ReEngageCron(URIHandler):
    def get(self):
        self.post()

    # TODO: This probably needs to use task queues...
    # TODO: How to make scheduling more flexible
    def post(self):
        """Posts all queue content to facebook on weekdays"""
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

            post_uuid = queue.queued[0]

            try:
                post = ReEngagePost.get(post_uuid)
            except Exception, e:
                # There was a problem getting the post.
                logging.error(e)
                continue

            cls  = POST_CLASSES.get(post.network, SocialNetwork)

            logging.info("Preparing post...")
            for product in products:
                logging.info("Sending content for %s..." % product)
                try:
                    cls.post(post, product=product)
                except Exception, e:
                    # Problem posting, no OpenGraph tag?
                    logging.error("Problem posting. Probably no OG tag for %s" % product.uuid)

            logging.info("Post: %s" % post_uuid)

            queue.expired.append(post_uuid)
            queue.queued.remove(post_uuid)
            queue.put()
