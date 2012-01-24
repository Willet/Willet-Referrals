#!/usr/bin/python

import logging

from apps.client.shopify.models import ClientShopify
from util.urihandler            import URIHandler

class FetchShopifyProducts( URIHandler ):
    """ Query the Shopify API to fetch all Products. """

    def get (self):
        self.post()

    def post( self ):
        logging.info("RUNNING client.shopify.processes::FetchShopifyProducts")
        logging.info("requested client = %s" % self.request.get('client'))
        logging.info("requested client_uuid = %s" % self.request.get('client_uuid'))
        logging.info("requested app_type = %s" % self.request.get( 'app_type' ))

        logging.debug ("checking ClientShopify by client")
        client   = ClientShopify.get_by_uuid( self.request.get('client') )
        if not client:
            logging.debug ("checking ClientShopify by client_uuid")
            client   = ClientShopify.get_by_uuid( self.request.get('client_uuid') )
        app_type = self.request.get( 'app_type' )

        client.get_products( app_type )

