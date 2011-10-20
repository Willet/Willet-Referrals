#!/usr/bin/env python

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc"

import logging, re, hashlib, urllib

from apps.app.models        import *
from apps.client.models     import ClientShopify
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

        client = ClientShopify.all().filter('url =', store_url).get()

        Email.emailBarbara("UNinstall app: %s\n%r %s" % (
                app_class_name,
                self.request, 
                self.request.headers
            )
        )
