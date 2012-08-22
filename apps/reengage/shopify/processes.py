import logging
from apps.product.shopify.processes import CreateProductShopify, UpdateProductShopify, DeleteProductShopify
from util.urihandler import URIHandler

class CreateReEngageProductShopify(URIHandler):
    """Create a Shopify product"""
    def post(self):
        logging.info("Calling method...")
        product = CreateProductShopify.create_product(self.request)
        logging.info("Creating product... %s" % product)
        product._get_or_create_queue()
        logging.info("Product queue... %s" % product.queue)


class UpdateReEngageProductShopify(URIHandler):
    """Update a Shopify product"""
    def post(self):
        product = UpdateProductShopify.update_product(self.request)
        logging.info("Creating product... %s" % product)
        product._get_or_create_queue()
        logging.info("Product queue... %s" % product.queue)


class DeleteReEngageProductShopify(URIHandler):
    """Delete a Shopify product"""
    def post(self):
        DeleteProductShopify.delete_product(self.request)