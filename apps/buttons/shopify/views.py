#!/usr/bin/env python
""" 'Get' functions for the ShopConnection application
"""
import logging
from collections                    import defaultdict
from datetime                       import date
from google.appengine.api           import taskqueue
from google.appengine.ext.webapp    import template
from apps.buttons.shopify.models    import ButtonsShopify, SharedItem, SharePeriod
from apps.client.shopify.models     import ClientShopify
from util.consts                    import *
from util.errors                    import ShopifyBillingError
from util.urihandler                import URIHandler
from apps.email.models              import Email
from util.helpers                   import url as build_url
from urlparse                       import urlparse
from django.utils                   import simplejson as json

#TODO: move these functions elsewhere.  More appropriate places would be...
def catch_error(fn):
    """Decorator for catching errors in ButtonsShopify install."""
    def wrapped(self):
        """Wrapped function, assumed to be a URI Handler."""
        client_email = ''
        shop_owner   = ''
        shop_name    = ''
        shop_url     = ''
        try:
            details = get_details(self)
            client_email = details["client_email"]
            shop_owner   = details["shop_owner"]
            shop_name    = details["shop_name"]
            shop_url     = details["shop_url"]

            fn(self)
        except Exception, e:
            logging.error('Smart-buttons install error, may require reinstall',
                  exc_info=True)

            # Email DevTeam
            Email.emailDevTeam(
                'Smart-buttons install error, may require reinstall: '\
                '%s, %s, %s, %s' %
                (client_email, shop_owner, shop_url, shop_name)
            )
            self.redirect ("%s?reason=%s" %
                           (build_url ('ButtonsShopifyInstallError'), e))
    return wrapped


def get_details(uri_handler=None, provided_client=None):
    """Given a URIHandler, returns a dictionary of details we expect."""
    if uri_handler is None and uri_handler.request is None:
        raise RuntimeError("No URI Handler provided!")

    request = uri_handler.request

    details = {}
    details["shop_url"] = request.get("shop") or request.get("shop_url")

    client = provided_client or ClientShopify.get_by_url(details["shop_url"])

    if client is not None and client.merchant is not None:
        details["client_email"] = client.email
        details["shop_owner"]   = client.merchant.get_full_name()
        details["shop_name"]    = client.name
        details["client"]       = client
    else:
        details["client_email"] = ""
        details["shop_owner"]   = "Shopify Merchant"
        details["shop_name"]    = "Your Shopify Store"
        details["client"]       = None

    return details


class ButtonsShopifyBeta(URIHandler):
    """If an existing customer clicks through from Shopify."""
    def get(self):
        """Display the default 'welcome' page."""
        template_values = {
            "SHOPIFY_API_KEY": SHOPIFY_APPS['ButtonsShopify']['api_key']
        }
        
        self.response.out.write(self.render_page('beta.html', template_values))


class ButtonsShopifyLearn(URIHandler):
    """ Video & blurb about premium ShopConnection """
    def get(self):
        """Display a page to learn more about smart buttons."""
        self.response.out.write(self.render_page('learn.html', {}))


class ButtonsShopifyWelcome(URIHandler):
    """After the installation process, provide an opportunity to upgrade."""
    @catch_error
    def get(self):
        """Display upgrade options."""
        token = self.request.get( 't' )
        details = get_details(self)

        if details["client"]:
            # Fetch or create the app
            app, created = ButtonsShopify.get_or_create_app(details["client"],
                                                            token=token)

            if created or not app.billing_enabled:
                price = app.get_price()

                template_values = {
                    'shop_owner' : details["shop_owner"],
                    'shop_name'  : details["shop_name"],
                    'price'      : price,
                    'shop_url'   : details["shop_url"],
                    'token'      : token,
                    'disabled'   : False,
                }

                self.show_upsell_page(**template_values)
            else:
                self.show_config_page(app, details)

        else:
            # Usually direct traffic to the url, show disabled version
            self.show_upsell_page()

    @catch_error
    def post(self):
        details = get_details(self)
        app = ButtonsShopify.get_by_url(details["shop_url"])
        if not app:
            logging.error("error updating preferences: "
                          "'app' not found. Install first?")


        preferences = {
            "button_count"  : (self.request.get("button-count") == "True"),
            "button_spacing": self.request.get("button-spacing"),
            "button_padding": self.request.get("button-padding")
        }

        app.update_prefs(preferences)

        #redirect to Welcome
        page = build_url("ButtonsShopifyWelcome", qs={
            "t"   : self.request.get("t"),
            "shop": self.request.get("shop"),
            "app" : "ButtonsShopify"
        })

        self.redirect(page)

    def show_upsell_page(self, shop_owner='Store Owner', shop_name='Store',
                         price='-.--', shop_url='www.example.com',
                         token="",
                         disabled=True):
        template_values = {
            'shop_owner' : shop_owner,
            'shop_name'  : shop_name,
            'price'      : price,
            'shop_url'   : shop_url,
            'token'      : token,
            'disabled'   : disabled,
        }

        self.response.out.write(self.render_page('upsell.html',
                                                 template_values))

    def show_config_page(self, app, details):
        # get values from datastore
        page = build_url("ButtonsShopifyWelcome", qs={
            "t"   : self.request.get("t"),
            "shop": self.request.get("shop"),
            "app" : "ButtonsShopify"
        })

        preferences = app.get_prefs()

        template_values = {
            'action'        : page,
            'button_count'  : preferences["button_count"],
            'button_spacing': preferences["button_spacing"],
            'button_padding': preferences["button_padding"]
        }

        # prepopulate values
        self.response.out.write(self.render_page('config.html', template_values))


class ButtonsShopifyUpgrade(URIHandler):
    """Starts the upgrade process."""
    @catch_error
    def get(self):
        """Begin the upgrade process."""
        details = get_details(self)

        existing_app = ButtonsShopify.get_by_url(details["shop_url"])
        if not existing_app:
            logging.error("error calling billing callback: "
                          "'existing_app' not found. Install first?")

        if existing_app.recurring_billing_price:
            price = existing_app.recurring_billing_price
        else:
            price = existing_app.get_price()

        # Start the billing process
        confirm_url = existing_app.setup_recurring_billing({
            "price":        price,
            "name":         "ShopConnection",
            "return_url":   "%s/b/shopify/billing_callback?app_uuid=%s" %
                            (URL, existing_app.uuid),
            "test":         USING_DEV_SERVER,
            "trial_days":   15
        })

        existing_app.put()

        if confirm_url:
            self.redirect(confirm_url)
            return
        else:
            # Can this even occur?
            raise ShopifyBillingError('No confirmation URL provided by '
                                      'Shopify API', {})


class ButtonsShopifyBillingCallback(URIHandler):
    """When a customer confirms / denies billing, they are redirected here.

    Activates billing with Shopify, then redirects customer to installation
    instructions.
    """
    @catch_error
    def get(self):
        """Activate the billing charges after Shopify has setup the charge."""

        app_uuid =self.request.get('app_uuid')
        app = ButtonsShopify.get_by_uuid(app_uuid)

        # Fetch the client
        # Since we cannot get the client until we have the app, in this case,
        # we pass in the client
        client  = ClientShopify.get_by_id(app.store_id)
        details = get_details(self, provided_client=client)

        if not app:
            logging.error("error calling billing callback: 'app' not found")

        charge_id = int(self.request.get('charge_id'))

        if charge_id != app.recurring_billing_id:
            raise ShopifyBillingError('Charge id in request does not match '
                                      'expected charge id',
                                      app.recurring_billing_id)

        # Good to go, activate!
        success = app.activate_recurring_billing({
            'return_url': self.request.url,
            'test': 'true'
        })

        if success:
            app.billing_enabled = True
            app.put()
            app.do_upgrade()

            template_values = {
                'app'        : app,
                'shop_owner' : details["shop_owner"],
                'shop_name'  : details["shop_name"]
            }

            # Render the page
            self.response.out.write(self.render_page('welcome.html',
                                                     template_values))
        else:
            #The user declined to pay, redirect to upsell page
            page = build_url("ButtonsShopifyWelcome", qs={
                "t": app.store_token,
                "shop": app.store_url,
                "app": "ButtonsShopify"
            })

            self.redirect(page)


class ButtonsShopifyInstructions(URIHandler):
    """Actions for the instructions page."""
    @catch_error
    def get( self ):
        """Displays post-installation instructions."""
        details = get_details(self)
        token  = self.request.get( 't' )
        client = details["client"]

        if not client or not token:
            self.error(400) # bad request
            return

        # update client token (needed when reinstalling)
        if client.token != token:
            logging.debug ("token was %s; updating to %s." %
                           (client.token if client else None, token))
            client.token = token
            client.put()

        # Fetch or create the app
        app, _ = ButtonsShopify.get_or_create_app(client, token=token)

        # Render the page
        template_values = {
            'app'          : app,
            'shop_owner'   : details["shop_owner"],
            'shop_name'    : details["shop_name"]
        }

        self.response.out.write(self.render_page('welcome.html',
                                                 template_values))


class ButtonsShopifyInstallError(URIHandler):
    """Actions for the error page."""
    def get (self):
        """Displays an error page for when the Buttons app fails to install
           or upgrade. Error emails are not handled by this page.
        """
        
        template_values = {
            'URL' : URL,
            'reason': self.request.get('reason', None),
        }
        self.response.headers.add_header('P3P', P3P_HEADER)
        self.response.headers['Content-Type'] = 'text/html; charset=utf-8'
        self.response.out.write(self.render_page('install_error.html',
                                                 template_values))
        return


class ButtonsShopifyServeScript(URIHandler):
    def get(self):
        path = os.path.join('apps/buttons/shopify/templates/js/',
                            'buttons.js')
        self.response.headers.add_header('P3P', P3P_HEADER)
        self.response.headers['Content-Type'] = 'application/javascript'
        self.response.out.write(template.render(path, {}))
        return


class ButtonsShopifyServeSmartScript(URIHandler):
    def get(self):
        path = os.path.join('apps/buttons/shopify/templates/js/',
                            'smart-buttons.js')
        self.response.headers.add_header('P3P', P3P_HEADER)
        self.response.headers['Content-Type'] = 'application/javascript'
        self.response.out.write(template.render(path, {}))
        return


class ButtonsShopifyItemShared(URIHandler):
    """Handles whenever a share takes place"""
    def get(self):
        """Handles a single share event.

        We assume that we receive one argument 'message' which is JSON
        of the following form:
            "name"    : name of the product
            "network" : network we are sharing on
            "img"     : url for time product image (optional)
        """
        product_page = self.request.headers.get('referer')

        # We only want the scheme and location to build the url
        store_url    = "%s://%s" % urlparse(product_page)[:2]

        message  = self.request.get('message')

        details = dict()
        try:
            details = json.loads(message)
        except:  # What Exception is thrown?
            logging.info("No JSON found / Unable to parse JSON!")

        app = ButtonsShopify.get_by_url(store_url)

        if app is not None:
            # Create a new share item
            item = SharedItem(details.get("name"),
                              details.get("network"),
                              product_page,
                              img_url=details.get("img"))

            share_period = SharePeriod.get_or_create(app);
            share_period.shares.append(item)
            share_period.put()

        else:
            logging.info("No app found!")

        self.redirect('%s/static/imgs/noimage.png' % URL)


class ButtonsShopifyEmailReports(URIHandler):
    """Queues the report emails"""
    def get(self):
        logging.info("Preparing reports...")

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

        share_period = SharePeriod.all()\
                        .filter('app_uuid =', app.uuid)\
                        .order('-end')\
                        .get()

        if share_period is None:
            logging.info("No share period found matching criteria")
            return

        shares_by_name    = share_period.get_shares_grouped_by_product()
        shares_by_network = share_period.get_shares_grouped_by_network()

        logging.info(shares_by_name)
        logging.info(shares_by_network)

        top_items        = sorted(shares_by_name,
                                  key=lambda v: v["total_shares"],
                                  reverse=True)[:10]
        top_shares       = sorted(shares_by_network,
                                  key=lambda v: v['shares'],
                                  reverse=True)

        logging.info(top_items)
        logging.info(top_shares)

        client = ClientShopify.get_by_url(store_url)
        if client is None or (client is not None and client.merchant is None):
            logging.info("No client!")
            return

        email = client.email
        shop  = client.name
        name  = client.merchant.get_full_name()

        Email.report_smart_buttons(email, top_items, top_shares,
                                 shop_name=shop, client_name=name)
