from apps.reengage.models import ReEngageCohort
from apps.analytics.utils import track_event
from apps.app.models import App
from apps.product.models import Product

from util.consts import *
from util.urihandler import URIHandler

import logging

class TrackEvent(URIHandler):
    """Log incoming event"""
    def get(self):
        return self.post()

    def post(self):
        """
        Logs event in the following format:
        [(string) category, (string) action, (string) label="app_uuid|pid=product_id|cid=cohort_uuid", (integer) value]
        """
        category = self.request.get('category')
        action = self.request.get('action')
        cohort_uuid = self.request.get('value')
        hostname = self.request.get('hostname')
        pathname = self.request.get('pathname')

        store_url = "http://%s" % hostname
        # try to find App associated with the event
        app = App.get_by_url(store_url)
        if not app:
            label = "unknown"
        else:
            label = "%s" % app.uuid

        # try to find product
        try:
            product_url = "%s%s" % (store_url, pathname[:pathname.index("leadspeaker_cohort_id=")])
        except:
            product_url = "%s%s" % (store_url, pathname)
        
        # exclude trailing slash
        if product_url[-1] == "/":
            product_url = product_url[:-1]

        product = Product.get_by_url(product_url)
        if product:
            label = "%s|pid=%s" % (label, product.uuid)

        # append cohort id if we have it
        if cohort_uuid:
            label = "%s|cid=%s" % (label, cohort_uuid)

        # finally, dump the event into GA
        track_event(category, action, label)
