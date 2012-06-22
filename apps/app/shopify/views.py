#!/usr/bin/env python

__author__ = "Willet, Inc."
__copyright__ = "Copyright 2011, Willet, Inc"

from time import time

from apps.app.models import *
from apps.client.shopify.models import ClientShopify, get_store_info
from apps.link.models import Link
from apps.user.models import User

from apps.order.models import *

from util.consts import *
from util.gaesessions import get_current_session
from util.helpers import *
from util.shopify_helpers import get_shopify_url
from util.urihandler import URIHandler

# The "Shows" -----------------------------------------------------------------
class ShopifyRedirect(URIHandler):
    # Renders a app page
    def get(self):
        # Request varZ from us
        app = self.request.get('app')

        # Request varZ from Shopify
        shopify_url = self.request.get('shop')
        shopify_sig = self.request.get('signature')
        store_token = self.request.get('t')
        shopify_timestamp = self.request.get('timestamp')

        if not (app and shopify_url and store_token):
            self.response.out.write('You are doing it wrong')
            logging.error('/a/shopify called incorrectly', exc_info=True)
            return

        # Get the store or create a new one
        client = ClientShopify.get_or_create(shopify_url, store_token, self, app)
        client_modified = False

        # Pivotal 27416355
        # fetch the Shopify store info to see if anything needs to be updated
        try:
            data = get_store_info(get_shopify_url(shopify_url), store_token, app)
            if client.email != data['email'] or client.name != data['name']:
                logging.debug('updating client information')
                client.email = data['email']
                client.name = data['name']
                client.put()
        except Exception, err:
            logging.error('could not update client info: %s' % err,
                          exc_info=True)

        # initialize session
        session = get_current_session()
        session.regenerate_id()

        # remember form values
        session['correctEmail'] = client.email
        session['email'] = client.email
        session['reg-errors'] = []

        logging.info("CLIENT: %s" % client.email)

        # Cache the client!
        self.db_client = client

        # TODO: apps on shopify have to direct properly
        # the app name has to corespond to AppnameWelcome view
        redirect_url = url('%sWelcome' % app)

        if redirect_url != None:
            redirect_url = '%s?%s' % (redirect_url, self.request.query_string)
        elif app == 'sibt':
            redirect_url = '/s/shopify?%s' % self.request.query_string
        elif app == 'buttons':
            redirect_url = '/b/shopify/welcome?%s' % self.request.query_string
        else:
            redirect_url = '/'
        logging.info("redirecting app %s to %s" % (app, redirect_url))
        self.redirect(redirect_url)

# The "Dos" -------------------------------------------------------------------
class DoDeleteApp(URIHandler):
    def post(self):
        client = self.get_client()
        app_uuid = self.request.get('app_uuid')

        logging.info('app id: %s' % app_uuid)
        app = App.get(app_uuid)
        if app.client.key() == client.key():
            logging.info('deleting')
            app.delete()

        self.redirect('/client/account')