#!/usr/bin/env python

__author__ = "Willet, Inc."
__copyright__ = "Copyright 2012, Willet, Inc"

import logging

from apps.client.models import Client
from apps.product.models import Product
from util.urihandler import URIHandler

class CreateProduct(URIHandler):
    """ Just a controller used to create a new product."""

    def get(self):
        """Allow <img src=???> requests to create products."""
        self.response.headers['Content-Type'] = 'image/gif'
        self.post()  # cross-domain compatibility

    def post(self):
        """ Required parameters:
            - client_uuid
            - (product URL) resource_url
            - (product name) title

            Optional parameters:
            - description
            - images (CSV)
            - tags (CSV)
            - price (defaults to 0.0 dollars)
        """

        # initialize vars
        client = Client.get(self.request.get("client_uuid"))
        description = self.request.get("description", "").strip()
        images = self.request.get("images", "").split(',')  # if empty string, -> [''] (True)
        price = float(self.request.get("price", "0.0"))
        resource_url = self.request.get("resource_url")
        tags = self.request.get("tags", "").split(',')
        title = self.request.get("title")
        type_ = self.request.get("type", "")

        if resource_url:
            logging.info("Old resource URL: %s" % resource_url)
            resource_url = resource_url.split('?')[0].strip('/')
            logging.info("New resource URL: %s" % resource_url)

        if not images[0] and self.request.get("image", ""):
            # thus, image url field must be non-empty
            images = [self.request.get("image")] # this is a list of one object

        # a None client will prevent creation
        if title and images and client:
            Product.get_or_create(# will not create again if it already exists
                title=title,
                description=description,
                images=images,
                price=price,
                client=client,
                resource_url=resource_url,
                type=type_,
                tags=tags
            )
            self.response.out.write("") # only care about headers
        else:
            logging.warn("Auto-create product failed: some required fields are missing")
            self.error(302)  # should be 400, but let browsers handle it
