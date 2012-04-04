#!/usr/bin/python

import logging

from apps.client.shopify.models import ClientShopify
from util.urihandler import URIHandler

class FetchShopifyProducts( URIHandler ):
    """ Query the Shopify API to fetch all Products. """

    def get (self):
        self.post()

    def post( self ):
        logging.info("RUNNING client.shopify.processes::FetchShopifyProducts")
        logging.debug("requested client = %s" % self.request.get('client'))
        logging.debug("requested client_uuid = %s" % self.request.get('client_uuid'))
        logging.debug("requested app_type = %s" % self.request.get( 'app_type' ))

        client = ClientShopify.get_by_uuid( self.request.get('client') )
        if not client:
            logging.debug ("Cannot find by client; checking by client_uuid")
            client = ClientShopify.get_by_uuid( self.request.get('client_uuid') )
        
        try:
            app_type = self.request.get( 'app_type' )
            client.get_products( app_type )
            self.response.out.write ("200 OK")
        except AttributeError:
            logging.error ('Client cannot be found.')
