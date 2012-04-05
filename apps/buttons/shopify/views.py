#!/usr/bin/env python

import logging

from google.appengine.ext           import webapp
from google.appengine.ext.webapp    import template
from urlparse                       import urlparse

from apps.buttons.shopify.models    import ButtonsShopify 
from apps.client.shopify.models     import ClientShopify
from util.consts                    import *
from util.errors                    import ShopifyBillingError
from util.urihandler                import URIHandler

class ButtonsShopifyBeta(URIHandler):
    """ If an existing customer clicks through from Shopify """
    def get(self):
        template_values = {
            "SHOPIFY_API_KEY": SHOPIFY_APPS['ButtonsShopify']['api_key']
        }
        
        self.response.out.write(self.render_page('beta.html', template_values))

class ButtonsShopifyWelcome(URIHandler):
    """ After the installation process, provide an opportunity to upgrade"""
    def get(self):
        try:
            # TODO: put this somewhere smarter
            shop   = self.request.get( 'shop' )
            token  = self.request.get( 't' )

            # Fetch the client
            client = ClientShopify.get_by_url( shop )

            # Fetch or create the app
            app    = ButtonsShopify.get_or_create_app(client, token=token)

            # Find out what the app should cost
            price = app.get_price()

            template_values = {
                'app'        : app,
                'shop_owner' : client.merchant.get_full_name(),
                'shop_name'  : client.name,
                'price'      : price,
                'shop_url'   : shop,
                'token'      : token,
            }
            
            self.response.out.write(self.render_page('upsell.html', template_values))
        except Exception, e:
            logging.error('SIbt install error, may require reinstall', exc_info=True)
            # Email DevTeam
            Email.emailDevTeam(
                'SIBT install error, may require reinstall: %s, %s, %s, %s' % 
                    (client_email, shop_owner, client.url, shop_name)
            )
            self.redirect ("%s?reason=%s" % (build_url ('ButtonsShopifyInstallError'), e))
            return

class ButtonsShopifyUpgrade(URIHandler):
    """ Starts the upgrade process """
    def get(self):
        try:
            shop_url = self.request.get("shop_url")

            existing_app = ButtonsShopify.get_by_url(shop_url)
            if not existing_app:
                logging.error("error calling billing callback: 'existing_app' not found. Install first?")

            if existing_app.recurring_billing_price:
                price = existing_app.recurring_billing_price
            else:
                price = existing_app.get_price()

            # Start the billing process
            confirm_url = existing_app.setup_recurring_billing({
                "price":        price,
                "name":         "ShopConnection",
                "return_url":   "%s/b/shopify/billing_callback?app_uuid=%s" % (URL, existing_app.uuid),
                "test":         USING_DEV_SERVER
            })

            existing_app.put()

            if confirm_url:
                self.redirect(confirm_url)
                return
            else:
                # Can this even occur?
                raise ShopifyBillingError('No confirmation URL provided by Shopify API', {})

        except Exception, e:
            logging.error('SIbt install error, may require reinstall', exc_info=True)
            # Email DevTeam
            Email.emailDevTeam(
                'SIBT install error, may require reinstall: %s, %s, %s, %s' % 
                    (client_email, shop_owner, client.url, shop_name)
            )
            self.redirect ("%s?reason=%s" % (build_url ('ButtonsShopifyInstallError'), e))
            return

class ButtonsShopifyBillingCallback(URIHandler):
    """ When a customer confirms / denies billing, they are redirected here

    Activates billing with Shopify, then redirects customer to installation instructions
    """
    def get(self):
        try:
            app_uuid =self.request.get('app_uuid')
            app = ButtonsShopify.get_by_uuid(app_uuid)

            if not app:
                logging.error("error calling billing callback: 'app' not found")

            charge_id = int(self.request.get('charge_id'))

            if charge_id == app.recurring_billing_id:
                # Good to go, activate!
                app.activate_recurring_billing({
                    'return_url': self.request.url,
                    'test': 'true'
                })
                app.billing_enabled = True

                app.put()

                app.do_upgrade()
            else:
                raise ShopifyBillingError('Charge id in request does not match expected charge id', app.recurring_billing_id)

            # Fetch the client
            client = ClientShopify.get_by_id(app.store_id)

            # Render the page
            template_values = {
                'app'        : app,
                'shop_owner' : client.merchant.get_full_name(),
                'shop_name'  : client.name
            }
            self.response.out.write(self.render_page('welcome.html', template_values))

        except Exception, e:
            logging.error('SIbt install error, may require reinstall', exc_info=True)
            # Email DevTeam
            Email.emailDevTeam(
                'SIBT install error, may require reinstall: %s, %s, %s, %s' % 
                    (client_email, shop_owner, client.url, shop_name)
            )
            self.redirect ("%s?reason=%s" % (build_url ('ButtonsShopifyInstallError'), e))
            return

class ButtonsShopifyInstructions(URIHandler):
    def get( self ):
        # TODO: put this somewhere smarter
        shop   = self.request.get( 'shop' )
        token  = self.request.get( 't' )

        # Fetch the client
        client = ClientShopify.get_by_url( shop )
    
        # Fetch or create the app
        app    = ButtonsShopify.get_or_create_app(client, token=token)

        # Render the page
        template_values = {
            'app'          : app,
            'shop_owner'   : client.merchant.get_full_name(),
            'shop_name'    : client.name
        }

        self.response.out.write(self.render_page('welcome.html', template_values))

class ButtonsShopifyError(URIHandler):
    def get (self):
        """ Displays an error page for when the Buttons app fails to install or upgrade. 
            Error emails are not handled by this page. 
        """
        
        template_values = {
            'URL' : URL,
            'reason': self.request.get('reason', None),
        }
        path = os.path.join('apps/buttons/shopify/templates/', 'install_error.html')
        self.response.headers.add_header('P3P', P3P_HEADER)
        self.response.headers['Content-Type'] = 'text/html; charset=utf-8'
        self.response.out.write(template.render(path, template_values))
        return