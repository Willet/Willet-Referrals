import logging
import datetime
from google.appengine.api import taskqueue
from apps.reengage.models import ReEngageQueue, ReEngagePost, ReEngageCohort, ReEngageCohortID, ReEngageShopify
from apps.reengage.social_networks import Facebook, SocialNetwork
from util.helpers import url
from util.urihandler import URIHandler

POST_CLASSES = {
    Facebook.__name__: Facebook,
}

class ReEngageCron(URIHandler):
    def get(self):
        self.post()

    def post(self):

        # WARNING: This will definitely blow up (exceed soft memory limit) on apps. It might not be obvious now, though.
        # TODO: Make this more performant
        # For the moment, assume that this represents all queues
        # ... It does not, but we'll replace this with .run() or a cursor
        #     or something else shortly
        marketing_plans  = ReEngageQueue.all().fetch(limit=1000)
        latest_cohort_id = ReEngageCohortID.get_latest()

        for marketing_plan in marketing_plans:
            # Create a new cohort for this week
            ReEngageCohort.create(marketing_plan)

            plan_length = len(marketing_plan.queued)
            cohorts     = marketing_plan.get_cohorts()

            for cohort in cohorts:
                logging.info("Cohort ID? %s" % cohort.cohort_id)
                logging.info("Latest ID? %s" % latest_cohort_id)
                if not cohort.cohort_id:
                    cohort.cohort_id = latest_cohort_id
                    cohort.put()

                message_index = cohort.message_index
                if message_index >= plan_length:
                    cohort.active = False
                    cohort.put()
                    continue

                taskqueue.add(url=url('ReEngageCronPostMessage'), params={
                    "index"         : message_index,
                    "plan_uuid"     : marketing_plan.uuid,
                    "cohort_uuid"   : cohort.uuid,
                })

        # Always create a new cohort at the end of a schedule...
        ReEngageCohortID.create()

        #...And update the snippets
        taskqueue.add(url=url('ReEngageUpdateSnippets'), params={})


class ReEngageCronPostMessage(URIHandler):
    def get(self):
        self.post()

    def post(self):
        index          = int(self.request.get("index"))
        plan_uuid      = self.request.get("plan_uuid")
        cohort_uuid    = self.request.get("cohort_uuid")

        marketing_plan = ReEngageQueue.get(plan_uuid)
        cohort         = ReEngageCohort.get(cohort_uuid)

        post_uuid      = marketing_plan.queued[index]
        plan_length    = len(marketing_plan.queued)

        products = marketing_plan.get_products()
        for product in products:
            post = ReEngagePost.get(post_uuid)
            try:
                cls = POST_CLASSES.get(post.network, SocialNetwork)
                cls.post(post, product=product, cohort=cohort.cohort_id)
            except NotImplementedError:
                logging.error("No 'post' method for class %s" % cls)
            except Exception, e:
                # Problem posting, no OpenGraph tag?
                logging.error("Problem posting. Probably no OG tag for %s" % product.uuid)

        cohort.message_index += 1
        if cohort.message_index >= plan_length:
            cohort.active = False
        cohort.put_later()


class ReEngageUpdateSnippets(URIHandler):
    def get(self):
        self.post()

    def post(self):
        latest_cohort_id = ReEngageCohortID.get_latest()

        # For the moment, assume that this represents all apps
        # ... It does not, but we'll replace this with .run() or a cursor
        #     or something else shortly
        apps = ReEngageShopify.all().fetch(1000)

        for app in apps:
            app.update_canonical_url(latest_cohort_id.uuid)