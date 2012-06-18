#!/usr/bin/env python
import datetime
import logging
from urlparse import urlparse
from google.appengine.api import taskqueue
from apps.buttons.shopify.models import ButtonsShopify, SharePeriod
from apps.client.shopify.models import ClientShopify
from apps.email.models import Email
from util.helpers import url as build_url
from util.urihandler import URIHandler

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2012, Willet, Inc"

class ButtonsShopifyEmailReports(URIHandler):
    """Queues the report emails"""
    def get(self):
        logging.info("Preparing reports...")

        # Do we want also want to filter by non-null clients too?
        apps = ButtonsShopify.all().filter(" billing_enabled = ", True)

        # Allows us to test the service while live.
        email = self.request.get("email")

        for app in apps:
            if hasattr(app, "unsubscribed") and app.unsubscribed:
                continue  # don't email unsubscribed people

            logging.info("Setting up taskqueue for %s" % app.client.name)
            params = {
                "store": app.store_url
            }

            if email:
                params.update({"email": email})

            url = build_url('ButtonsShopifyItemSharedReport')
            logging.info("taskqueue URL: %s" % url)
            taskqueue.add(queue_name='buttonsEmail', url=url, params=params)


class ButtonsShopifyItemSharedReport(URIHandler):
    """Sends individual emails"""
    def get(self):
        self.post()

    def post(self):
        product_page = self.request.get('store')

        # We only want the scheme and location to build the url
        store_url    = "%s://%s" % urlparse(product_page)[:2]
        app = ButtonsShopify.get_by_url(store_url)

        logging.info("Preparing individual report for %s..." % store_url)

        if app is None:
            logging.info("App not found!")
            return

        client = ClientShopify.get_by_url(store_url)
        if client is None:
            logging.info("No client!")
            return

        merchant = None
        try:
            merchant = client.merchant
        except TypeError:
            # Client has no merchant
            logging.error("Client %r has no merchant.  Using fake values" % (client,))

        email = client.email
        shop  = client.name
        if merchant is not None:
            name  = client.merchant.get_full_name()
        else:
            name  = "Shopify Merchant"

        share_period = SharePeriod.all()\
                        .filter('app_uuid =', app.uuid)\
                        .order('-end')\
                        .get()

        # Allows us to test the service while live.
        email = self.request.get("email", email)

        if share_period is None or (share_period.end < datetime.date.today()):
            logging.info("No shares have ever occured this period (or ever?)")
            Email.report_smart_buttons(email=email, items={}, networks={},
                                       shop_name=shop,
                                       client_name=name, uuid=app.uuid)
            return

        shares_by_name    = share_period.get_shares_grouped_by_product()
        shares_by_network = share_period.get_shares_grouped_by_network()

        top_items  = sorted(shares_by_name, key=lambda v: v["total_shares"],
                            reverse=True)[:3]
        top_shares = sorted(shares_by_network, key=lambda v: v['shares'],
                            reverse=True)

        Email.report_smart_buttons(email=email, items=top_items,
                                   networks=top_shares,
                                   shop_name=shop, client_name=name,
                                   uuid=app.uuid)


class ButtonsShopifyUnsubscribe(URIHandler):
    def get(self):
        uuid = self.request.get("uuid")
        app = ButtonsShopify.all().filter(" uuid = ", uuid).get()

        unsubscribed = True
        if app:
            unsubscribed = app.unsubscribed

        template_values = self.response.out.write(self.render_page('unsubscribe.html', {
            'uuid': uuid,
            'unsubscribed': unsubscribed,
            'app_exists': True if app else False
        }))

    def post(self):
        uuid = self.request.get("uuid")

        app = ButtonsShopify.all().filter(" uuid = ", uuid).get()

        if app:
            app.unsubscribed = True
            app.put()

        template_values = {
            "unsubscribed": True,
            'app_exists': True if app else False
        }

        self.response.out.write(self.render_page('unsubscribe.html',
                                                 template_values))