#!/usr/bin/env python
""" 'Get' functions for the ShopConnection application
"""
import datetime
import logging
from urlparse import urlparse

from django.utils import simplejson as json
from django.utils.html import strip_tags

from apps.buttons.shopify.models import ButtonsShopify, SharedItem, SharePeriod
from apps.client.shopify.models import ClientShopify
from apps.email.models import Email

from util.consts import *
from util.errors import ShopifyBillingError
from util.helpers import url as build_url
from util.shopify_helpers import get_shopify_url
from util.urihandler import URIHandler

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
    client = merchant = None
    details = {}
    details["shop_url"] = request.get("shop") or request.get("shop_url")
    details["shop_url"] = get_shopify_url(details["shop_url"])  # fix domain

    client = provided_client or ClientShopify.get_by_url(details["shop_url"])

    if client:
        try:
            # Merchant is a referenced model, so this implicitly does a memcache and/or db get
            merchant = client.merchant
        except TypeError:
            # Client has no merchant
            logging.error("Client %r has no merchant.  Using fake values" % (client,))

    if client is not None and merchant is not None:
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
    def get(self, _beta):
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
        token  = self.request.get( 't' )
        upsell = (self.request.get( 'more' ) == "1")
        details = get_details(self)

        if details["client"]:
            # Fetch or create the app
            app, created = ButtonsShopify.get_or_create(details["client"],
                                                        token=token)

            if created or upsell:
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
                page = build_url("ButtonsShopifyConfig", qs={
                    "t"   : app.store_token,
                    "shop": app.store_url,
                    "app" : "ButtonsShopify"
                })
                self.redirect(page)

        else:
            # Usually direct traffic to the url, show disabled version
            self.show_upsell_page()

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

        # charge the app the same price as we promised back then, even
        # if it is cheaper now?
        if existing_app.recurring_billing_price:
            price = existing_app.recurring_billing_price
        else:
            price = existing_app.get_price()

        # Start the billing process
        confirm_url = existing_app.setup_recurring_billing({
            "price":        price,
            "name":         "ShopConnection",
            "return_url":   "%s%s?app_uuid=%s" % (URL,
                                                  build_url('ButtonsShopifyBillingCallback'),
                                                  existing_app.uuid),
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


class ButtonsShopifyTailoredInstall(URIHandler):
    """View where the user goes to pay us 8 sweet dollars (2 to Shopify)."""
    @catch_error
    def get(self):
        """Begin the upgrade process."""
        price = 10.0  # "we're charging people ten bucks to install it for em"

        app = ButtonsShopify.get_by_url(self.request.get('store_url', ''))
        if not app:
            logging.error("ButtonsShopifyTailoredInstall: "
                          "I don't think you're calling it right")

        # Start the billing process
        callback = build_url('ButtonsShopifyOneTimeBillingCallback')
        return_url = app.setup_one_time_billing({
            "price": price,
            "name": "ShopConnection",
            "return_url": "%s%s?app_uuid=%s" % (URL, callback, app.uuid),
            "test": USING_DEV_SERVER
        })

        if return_url:
            self.redirect(return_url)  # client then goes to confirm the charge
            return
        else:
            raise ShopifyBillingError('No confirmation URL provided by '
                                      'Shopify API', {})


class ButtonsShopifyOneTimeBillingCallback(URIHandler):
    """When a customer confirms / denies billing, they are redirected here.

    Activates billing with Shopify, then redirects customer to installation
    instructions.
    """
    @catch_error
    def get(self):
        """Activate the billing charges after Shopify has setup the charge."""

        app_uuid = self.request.get('app_uuid')
        app = ButtonsShopify.get_by_uuid(app_uuid)


        if not app:
            logging.error("error calling billing callback: 'app' not found")

        client  = app.client
        charge_id = int(self.request.get('charge_id'))

        '''
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

            # Render the page
            page = build_url("ButtonsShopifyInstructions", qs={
                "t"   : app.store_token,
                "shop": app.store_url,
                "app" : "ButtonsShopify"
            })
            self.redirect(page)

        else:
            #The user declined to pay, redirect to upsell page
            page = build_url("ButtonsShopifyWelcome", qs={
                "t"   : app.store_token,
                "shop": app.store_url,
                "app" : "ButtonsShopify"
            })

            self.redirect(page)
        '''


class ButtonsShopifyBillingCallback(URIHandler):
    """When a customer confirms / denies billing, they are redirected here.

    Activates billing with Shopify, then redirects customer to installation
    instructions.
    """
    @catch_error
    def get(self):
        """Activate the billing charges after Shopify has setup the charge."""

        app_uuid = self.request.get('app_uuid')
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

            # Render the page
            page = build_url("ButtonsShopifyInstructions", qs={
                "t"   : app.store_token,
                "shop": app.store_url,
                "app" : "ButtonsShopify"
            })
            self.redirect(page)

        else:
            #The user declined to pay, redirect to upsell page
            page = build_url("ButtonsShopifyWelcome", qs={
                "t"   : app.store_token,
                "shop": app.store_url,
                "app" : "ButtonsShopify"
            })

            self.redirect(page)


class ButtonsShopifyInstructions(URIHandler):
    """Actions for the instructions page."""
    @catch_error
    def get(self):
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
        app, _ = ButtonsShopify.get_or_create(client, token=token)

        config_enabled = app.billing_enabled
        config_url     = build_url("ButtonsShopifyConfig", qs={
            "t": app.store_token,
            "shop": app.store_url,
            "app": "ButtonsShopify"
        })

        # Render the page
        template_values = {
            'app'           : app,
            'shop_owner'    : details["shop_owner"],
            'shop_name'     : details["shop_name"],
            'config_enabled': config_enabled,
            'config_url'    : config_url
        }

        self.response.out.write(self.render_page('welcome.html',
                                                 template_values))


class ButtonsShopifyConfig(URIHandler):
    """Actions for the config page."""
    button_range = range(2, 6)

    def determine_buttons(self, preferences):
        buttons         = set(['Facebook', 'Fancy', 'GooglePlus', 'Pinterest',
                               'Svpply', 'Tumblr', 'Twitter'])
        button_order    = preferences.get("button_order",
            ["Pinterest","Tumblr","Fancy"])

        # That's right! TAKE THAT MATH-HATERS!
        unused_buttons  = buttons.difference(button_order)

        return (button_order, unused_buttons)

    def get_button_shares(self, app):
        share_period = SharePeriod.all()\
            .filter('app_uuid =', app.uuid)\
            .order('-end')\
            .get()

        if share_period is None or (share_period.end < datetime.date.today()):
            logging.info("No shares have ever occured this period (or ever?)")
            return ({}, {})

        shares_by_name    = share_period.get_shares_grouped_by_product()
        shares_by_network = share_period.get_shares_grouped_by_network()

        top_items  = sorted(shares_by_name, key=lambda v: v["total_shares"],
                            reverse=True)[:3]
        top_shares = sorted(shares_by_network, key=lambda v: v['shares'],
                            reverse=True)

        return (top_items, top_shares)

    @catch_error
    def get(self):
        """Display the config page for first use"""
        token = self.request.get( 't' )
        details = get_details(self)
        app, _ = ButtonsShopify.get_or_create(details["client"],
                                                  token=token)

        query_params = {
            "t"   : self.request.get("t"),
            "shop": self.request.get("shop"),
            "app" : "ButtonsShopify"
        }

        config_url       = build_url("ButtonsShopifyConfig", qs=query_params)
        instructions_url = build_url("ButtonsShopifyInstructions", qs=query_params)
        upgrade_url      = build_url("ButtonsShopifyUpgrade", qs=query_params)
        learn_more_url   = build_url("ButtonsShopifyWelcome", qs={
            "t"   : self.request.get("t"),
            "shop": self.request.get("shop"),
            "app" : "ButtonsShopify",
            "more": 1
        })

        preferences = app.get_prefs()

        button_order, unused_buttons = self.determine_buttons(preferences)
        item_shares, network_shares  = self.get_button_shares(app)

        # Use .get in case properties don't exist yet
        template_values = {
            'action'          : config_url,
            'max_buttons'     : preferences.get("max_buttons", 3),
            'button_range'    : self.button_range,
            'button_count'    : preferences.get("button_count", False),
            'button_spacing'  : preferences.get("button_spacing", 5),
            'button_padding'  : preferences.get("button_padding", 5),
            'sharing_message' : preferences.get("sharing_message", ""),
            'message'         : self.request.get("message", "Welcome Back!"),
            'button_order'    : button_order,
            'unused_buttons'  : unused_buttons,
            'shop_url'        : self.request.get("shop"),
            'upgrade_url'     : upgrade_url,
            'learn_more_url'  : learn_more_url,
            'instructions_url': instructions_url,
            'config_enabled'  : app.billing_enabled,
            'item_shares'     : item_shares,
            'network_shares'  : network_shares
        }

        # prepopulate values
        self.response.out.write(self.render_page('config.html', template_values))

    @catch_error
    def post(self):
        """Store the results from the config form"""
        r = self.request
        details = get_details(self)
        config_url = build_url("ButtonsShopifyConfig", qs={
            "t"   : self.request.get("t"),
            "shop": self.request.get("shop"),
            "app" : "ButtonsShopify",
            "message": "Your configuration was saved successfully!"
        })

        app = ButtonsShopify.get_by_url(details["shop_url"])
        if not app:
            logging.error("error updating preferences: "
                          "'app' not found. Install first?")

        if not app.billing_enabled:
            #Somehow, they've posted without having paid. Ignore the request.
            self.redirect(config_url)

        # TODO: Find a generic way to validate arguments
        def tryParse(func, val, default_value=0):
            try:
                return func(val)
            except:
                return default_value

        prefs = {}
        prefs["button_count"]    = (r.get("button_count") == "True")
        prefs["button_spacing"]  = tryParse(int, r.get("button_spacing"))
        prefs["button_padding"]  = tryParse(int, r.get("button_padding"))
        prefs["sharing_message"] = tryParse(strip_tags,
                                            r.get("sharing_message"), "")
        max_buttons              = tryParse(int, r.get("max_buttons"), 3)

        if max_buttons in self.button_range:
            prefs["max_buttons"] = max_buttons
        else:
            prefs["max_buttons"] = 3 #Default

        # What validation should be done here?
        prefs["button_order"]    = r.get("button_order").split(",")

        app.update_prefs(prefs)
        self.redirect(config_url)


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

            share_period = SharePeriod.get_or_create(app)
            share_period.shares.append(item)
            share_period.put()

        else:
            logging.info("No app found!")

        self.redirect('%s/static/imgs/noimage.png' % URL)


