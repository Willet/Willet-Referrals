#!/usr/bin/env python

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2012, Willet, Inc"

import logging

from apps.client.models import Client
from apps.product.models import Product
from util.urihandler import URIHandler

class CreateProduct(URIHandler):
    ''' 
        Just a controller used to create a new product.
    '''
    
    def get(self):
        self.post()
    
    def post(self):
        try:
            title = self.request.get("title")
            description = self.request.get("description", "")
            type = self.request.get("type", "")
            price = float(self.request.get("price", "0.0"))
            resource_url = self.request.get("resource_url")
            client = Client.get(self.request.get("client_uuid")) # a None client will stop creation
            images = self.request.get("images", "").split(',') # if empty string, -> [''] (True)
            tags = self.request.get("tags", "").split(',')

            if not images[0] and self.request.get("image", ""): # thus, image url field must be non-empty
                images = [self.request.get("image")] # this is a list of one object
            
            if title and description and images and price and client:
                Product.get_or_create( # will not create again if it already exists 
                    title=title,
                    description=description,
                    images=images,
                    price=price,
                    client=client,
                    resource_url=resource_url,
                    type=type,
                    tags=tags
                )
                self.response.out.write("OK") # only care about headers
            else:
                logging.warn("Auto-create product failed: some required fields are missing")
                self.error(400)
        except Exception, e:
            logging.error("Error auto-creating product: %s" % e, exc_info=True)
            self.error(500) # something went wrong, but it is nobody's concern
