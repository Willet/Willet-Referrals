#!/usr/bin/env python
""" 'Get' functions for the ShopConnection application
"""

from logging                        import error
from google.appengine.ext.webapp    import template
from apps.buttons.shopify.models    import ButtonsShopify 
from apps.client.shopify.models     import ClientShopify
from util.consts                    import *
from util.errors                    import ShopifyBillingError
from util.urihandler                import URIHandler
from apps.email.models              import Email
from util.helpers                   import url as build_url

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
            error('Smart-buttons install error, may require reinstall',
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

    details = dict()
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

        # Fetch or create the app
        app = ButtonsShopify.get_or_create_app(details["client"], token=token)

        # Find out what the app should cost
        price = app.get_price()

        template_values = {
            'app'        : app,
            'shop_owner' : details["shop_owner"],
            'shop_name'  : details["shop_name"],
            'price'      : price,
            'shop_url'   : details["shop_url"],
            'token'      : token,
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
            error("error calling billing callback: "
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
            error("error calling billing callback: 'app' not found")

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
        app    = ButtonsShopify.get_or_create_app(client, token=token)

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