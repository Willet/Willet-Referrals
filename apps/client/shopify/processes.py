#!/usr/bin/python

import logging

from apps.client.shopify.models import ClientShopify
from util.urihandler            import URIHandler

class FetchShopifyProducts( URIHandler ):
    """ Query the Shopify API to fetch all Products. """

    def post( self ):
        logging.info("RUNNING")
        client   = ClientShopify.get_by_uuid( self.request.get('client_uuid') )
        app_type = self.request.get( 'app_type' )

        client.get_products( app_type )
