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

        for app in apps:
            logging.info("Setting up taskqueue for %s" % app.client.name)
            params = {
                "store": app.store_url,
            }
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
        if client is None or (client is not None and client.merchant is None):
            logging.info("No client!")
            return

        email = client.email
        shop  = client.name
        name  = client.merchant.get_full_name()

        share_period = SharePeriod.all()\
                        .filter('app_uuid =', app.uuid)\
                        .order('-end')\
                        .get()

        if share_period is None or (share_period.end < datetime.date.today()):
            logging.info("No shares have ever occured this period (or ever?)")
            Email.report_smart_buttons(email, {}, {},
                                       shop_name=shop,
                                       client_name=name)
            return

        shares_by_name    = share_period.get_shares_grouped_by_product()
        shares_by_network = share_period.get_shares_grouped_by_network()

        top_items  = sorted(shares_by_name, key=lambda v: v["total_shares"],
                            reverse=True)[:10]
        top_shares = sorted(shares_by_network, key=lambda v: v['shares'],
                            reverse=True)



        Email.report_smart_buttons(email, top_items, top_shares,
                                   shop_name=shop, client_name=name)