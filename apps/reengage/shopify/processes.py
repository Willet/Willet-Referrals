import logging
from apps.product.shopify.processes import \
    create_product, update_product, delete_product, \
    create_collection, update_collection, delete_collection
from util.urihandler import URIHandler

#TODO: We should just get_or_create the product instead of duplicating
# existing webhooks

class CreateReEngageProductShopify(URIHandler):
    """Create a Shopify product"""
    def post(self):
        logging.info("Calling method...")
        product = create_product(self.request)
        logging.info("Creating product... %s" % product)
        queue = product.queue
        logging.info("Product queue... %s" % queue)


class UpdateReEngageProductShopify(URIHandler):
    """Update a Shopify product"""
    def post(self):
        product = update_product(self.request)
        logging.info("Creating product... %s" % product)
        queue = product.queue
        logging.info("Product queue... %s" % queue)


class DeleteReEngageProductShopify(URIHandler):
    """Delete a Shopify product"""
    def post(self):
        delete_product(self.request)


class CreateReEngageCollectionsShopify(URIHandler):
    """Create a Shopify collection"""
    def post(self):
        create_collection(self.request)


class UpdateReEngageCollectionsShopify(URIHandler):
    """Update a Shopify collection"""
    def post(self):
        update_collection(self.request, force_update=True)


class DeleteReEngageCollectionsShopify(URIHandler):
    """Delete a Shopify collection"""
    def post(self):
        delete_collection(self.request)