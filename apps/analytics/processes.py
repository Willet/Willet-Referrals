from apps.app.models import App
from apps.analytics.utils import track_event
from apps.product.models import Product

from util.urihandler import URIHandler


class TrackEvent(URIHandler):
    """Logs incoming event into Google analytics.

    Events are logged in the following format:
    [
        (string) category,
        (string) action,
        (string) label="app_uuid|pid=product_id|cid=cohort_uuid",
        (integer) value

        pid and cid parameters in the label are optional
    ]
    """
    def get(self):
        return self.post()

    def post(self):
        category = self.request.get('category')
        action = self.request.get('action')
        cohort_uuid = self.request.get('value')
        hostname = self.request.get('hostname')
        pathname = self.request.get('pathname')

        # default value
        label = "unknown"
        if hostname:
            store_url = "http://%s" % hostname
            # try to find App associated with the event
            app = App.get_by_url(store_url)
            if app:
                label = app.uuid

        # try to find product
        try:
            product_url = "%s%s" % (store_url,
                                    pathname[:pathname.index("leadspeaker_cohort_id=")])
        except ValueError:
            product_url = "%s%s" % (store_url, pathname)

        # exclude trailing slash
        product_url = product_url.rstrip("/")

        product = Product.get_by_url(product_url)
        if product:
            label = "%s|pid=%s" % (label, product.uuid)

        # append cohort id if we have it
        if cohort_uuid:
            label = "%s|cid=%s" % (label, cohort_uuid)

        # finally, dump the event into GA
        track_event(category, action, label)
