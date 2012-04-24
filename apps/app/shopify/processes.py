#!/usr/bin/env python

__author__ = "Willet, Inc."
__copyright__ = "Copyright 2011, Willet, Inc"

import logging
import datetime

from apps.app.models import *
from apps.client.shopify.models import ClientShopify
from apps.email.models import Email

from util.consts import *
from util.helpers import *
from util.urihandler import URIHandler


class DoUninstalledApp(URIHandler):
    def post(self, app_name):
        # Grab the ShopifyApp
        uninstalled_apps_count = 0
        store_url = self.request.headers['X-Shopify-Shop-Domain']
        logging.info("Uninstalling %s for store: %s " % (app_name, store_url))
        app_class_name = app_name
        duration = 'unknown'
        price = 'n/a'

        client = ClientShopify.get_by_url(store_url)
        if not client:
            logging.error('Cannot uninstall %s: client for store %s is gone from DB' % \
                           (app_class_name, store_url))
            return

        # "Delete" the App
        apps = client.apps
        for app in apps:
            if app.class_name() == app_class_name:
                # put client aside to keep record
                # (None client means "not installed")
                try:
                    duration = (datetime.datetime.utcnow() - app.created).days
                except:
                    logging.error("Could not create install duration", exc_info=True)
                    pass

                if hasattr(app, 'recurring_billing_status'):
                    app.recurring_billing_status = 'none'
                if hasattr(app, 'recurring_billing_enabled'):
                    app.recurring_billing_enabled = False
                if hasattr(app, 'recurring_billing_id'):
                    app.recurring_billing_id = 0
                if hasattr(app, 'recurring_billing_price'):
                    price = app.recurring_billing_price or 'n/a'
                    app.recurring_billing_price = ''

                app.old_client = client
                app.client = None
                app.put_later()

                uninstalled_apps_count += 1
        
        if uninstalled_apps_count:
            # Stop sending email updates
            if app_name in SHOPIFY_APPS and 'mailchimp_list_id' in SHOPIFY_APPS[app_name]:
                client.unsubscribe_from_mailing_list(
                    list_name=app_name,
                    list_id=SHOPIFY_APPS[app_name]['mailchimp_list_id']
                )

            try:
                Email.emailDevTeam("""<p>%s Uninstall</p>
                                      <p>Store: %s</p>
                                      <p>Installed for %s days</p>
                                      <p>Paying: %s</p>""" % ( app_class_name,
                                                               store_url,
                                                               duration,
                                                               price ) )

                # Say goodbye from Fraser
                Email.goodbyeFromFraser(client.merchant.get_attr('email'),
                                        client.merchant.get_attr('full_name'),
                                        app_class_name)
            except AttributeError, e: # e.g. merchant is missing from client
                logging.warn('Could not email client: %s' % e, exc_info=True)
                # this lets us send a 200 OK to Shopify anyway to tell them
                # nothing bad happened to our webhooks
        else:
            logging.warn('No apps uninstalled! (Are they in DB?)')
        
        return
