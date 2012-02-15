#!/usr/bin/env python

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc"

import logging, re, hashlib, urllib

from apps.app.models        import *
from apps.client.shopify.models import ClientShopify
from apps.email.models      import Email

from util.helpers           import *
from util.urihandler        import URIHandler
from util.consts            import *

class DoUninstalledApp( URIHandler ):
    def post(self, app_name):
        # Grab the ShopifyApp
        store_url = self.request.headers['X-Shopify-Shop-Domain']
        logging.info("store: %s " % store_url)
        app_class_name = SHOPIFY_APPS[app_name]['class_name'] 

        client = ClientShopify.get_by_url( store_url )

        Email.emailDevTeam("UNinstall app: %s\n%r %s" % (
                app_class_name,
                self.request, 
                self.request.headers
            )
        )

        # Say goodbye from Fraser
        Email.goodbyeFromFraser( client.merchant.get_attr( 'email' ),
                                 client.merchant.get_attr( 'full_name' ),
                                 app_class_name )

        # "Delete" the App
        apps = client.apps
        for a in apps:
            logging.info('%s %s' % (a.class_name(), app_class_name))
            if a.class_name() == app_class_name:
                a.old_client = client
                a.client     = None
                a.put()
