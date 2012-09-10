import logging
from google.appengine.api import taskqueue
from apps.client.models import Client
from apps.product.models import Product
from apps.product.shopify.models import ProductShopifyCollection
from apps.product.shopify.processes import \
    create_product, update_product, delete_product, \
    create_collection, update_collection, delete_collection
from util.helpers import url
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


class GetOrCreateShopifyQueues(URIHandler):
    """Creates missing queues"""
    def get(self):
        self.post()

    def post(self):
        """Creates missing queues.

        get_or_create_queue is expensive. So, do it with taskqueues"""

        client_uuid = self.request.get("client_uuid")

        client = Client.get(client_uuid)

        if not client:
            raise ValueError("No client found for client_uuid: %s" % client_uuid)

        for collection in client.collections:
            taskqueue.add(url=url("GetOrCreateShopifyQueue"), params={
                "uuid": collection.uuid,
                "type": "Collection"
            })

        for product in client.products:
            taskqueue.add(url=url("GetOrCreateShopifyQueue"), params={
                "uuid": product.uuid,
                "type": "Product"
            })

        self.response.out.write("OK")


class GetOrCreateShopifyQueue(URIHandler):
    """Creates missing queues"""
    def get(self):
        self.post()

    def post(self):
        """Creates missing queues.

        get_or_create_queue is expensive. So, do it with taskqueues"""
        uuid = self.request.get("uuid")
        type = self.request.get("type")

        if type == "Collection":
            object = ProductShopifyCollection.get(uuid)
        elif type == "Product":
            object = Product.get(uuid)
        else:
            logging.error("Incompatible type: %s" % type)
            return

        if not object:
            logging.error("No %s found for col_uuid: %s" % (type, uuid))
            return

        # Implicitly does _get_or_create_queue()
        queue = object.queue

        self.response.out.write("OK")