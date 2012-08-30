import logging
import datetime
from google.appengine.ext import db
from google.appengine.api import taskqueue
from apps.reengage.models import ReEngageQueue, ReEngagePost, ReEngageCohort
from apps.reengage.social_networks import Facebook, SocialNetwork
from util.helpers import generate_uuid, url
from util.urihandler import URIHandler

POST_CLASSES = {
    Facebook.__name__: Facebook,
}

class ReEngageOldCron(URIHandler):
    def get(self):
        self.post()

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
                except NotImplementedError:
                    logging.error("No 'post' method for class %s" % cls)
                except Exception, e:
                    # Problem posting, no OpenGraph tag?
                    logging.error("Problem posting. Probably no OG tag for %s" % product.uuid)

            logging.info("Post: %s" % post_uuid)

            queue.expired.append(post_uuid)
            queue.queued.remove(post_uuid)
            queue.put()


class ReEngageCron(URIHandler):
    def get(self):
        self.post()

    def post(self):

        # For the moment, assume that this represents all queues
        # ... It does not, but we'll replace this with .run() or a cursor
        #     or something else shortly
        marketing_plans = ReEngageQueue.all().fetch(limit=1000)

        for marketing_plan in marketing_plans:
            cohorts     = marketing_plan.get_cohorts()
            plan_length = len(marketing_plan.queued)

            for cohort in cohorts:
                message_index = cohort.message_index
                if message_index >= plan_length:
                    cohort.active = False
                    cohort.put()
                    continue

                taskqueue.add(url=url('ReEngageCronPostMessage'), params={
                    "index"      : message_index,
                    "plan_uuid"  : marketing_plan.uuid,
                    "cohort_uuid": cohort.uuid
                })

            # Always create a new cohort at the end of a schedule
            uuid = generate_uuid(16)
            cohort = ReEngageCohort(
                queue = marketing_plan,
                uuid  = uuid
            )
            cohort.put()

            marketing_plan.cohorts.append(unicode(uuid))
            marketing_plan.put()



class ReEngageCronPostMessage(URIHandler):
    def get(self):
        self.post()

    def post(self):
        index       = self.request.get("index")
        plan_uuid   = self.request.get("plan_uuid")
        cohort_uuid = self.request.get("cohort_uuid")

        marketing_plan = ReEngageQueue.get(plan_uuid)
        cohort         = ReEngageCohort.get(cohort_uuid)

        post_uuid      = marketing_plan.queued[index]
        plan_length    = len(marketing_plan.queued)

        for product in marketing_plan.products:
            post = ReEngagePost.get(post_uuid)
            try:
                cls = POST_CLASSES.get(post.network, SocialNetwork)
                cls.post(post, product=product, cohort=cohort)
            except NotImplementedError:
                logging.error("No 'post' method for class %s" % cls)
            except Exception, e:
                # Problem posting, no OpenGraph tag?
                logging.error("Problem posting. Probably no OG tag for %s" % product.uuid)

        cohort.message_index += 1
        if cohort.message_index >= plan_length:
            cohort.active = False
        cohort.put()
