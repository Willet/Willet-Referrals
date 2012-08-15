import logging
import datetime

from google.appengine.api import taskqueue
from apps.product.models import ProductCollection

from apps.reengage.models import ReEngageQueue, ReEngagePost, ReEngageSchedule
from apps.reengage.social_networks import Facebook, SocialNetwork

from util.urihandler import URIHandler
from util.helpers import url as build_url

POST_CLASSES = {
    Facebook.__name__: Facebook,
}

class ReEngageCron(URIHandler):
    def get(self):
        self.post()

    def post(self):
        today   = datetime.datetime.utcnow()
        weekday = today.weekday()

        schedules = ReEngageSchedule.all()\
                    .filter('days = ', weekday)\
                    .filter('times = ', today.hour)

        for schedule in schedules:
            queue = schedule.queue
            if not queue.queued:
                logging.info("No messages queued, continuing...")
                continue

            products = queue.get_products()
            if not products:
                logging.info("No products associated with queue, continuing...")
                continue

            uuid          = queue.queued[0]
            url           = build_url('ReEngagePostProduct')
            params        = {"post": uuid}
            retry_options = {"task_retry_limit": 0}

            for product in products:
                params.update({"product": product.uuid})
                taskqueue.add(queue_name='buttonsEmail', url=url,
                              params=params, retry_options=retry_options)

            queue.expired.append(uuid)
            queue.queued.remove(uuid)
            queue.put()



    def post2(self):
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
                except NotImplementedError:
                    logging.error("No 'post' method for class %s" % cls)
                except Exception, e:
                    # Problem posting, no OpenGraph tag?
                    logging.error("Problem posting. Probably no OG tag for %s" % product.uuid)

            logging.info("Post: %s" % post_uuid)

            queue.expired.append(post_uuid)
            queue.queued.remove(post_uuid)
            queue.put()


class ReEngagePostProduct(URIHandler):
    def get(self):
        self.post()

    def post(self):
        post_uuid    = self.request.get("post")
        product_uuid = self.request.get("product")

        try:
            post = ReEngagePost.get(post_uuid)
            product = ProductCollection.get(product_uuid)

            network  = POST_CLASSES.get(post.network, SocialNetwork)
            network.post(post, product=product)
        except NotImplementedError, e:
            logging.error("Not implemented error: %s" % e)
        except Exception, e:
            logging.error("Problem posting. %s" % e)

