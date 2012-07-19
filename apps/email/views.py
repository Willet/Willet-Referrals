#!/usr/bin/env python

__author__ = "Willet Inc."
__copyright__ = "Copyright 2012, The Willet Corporation"

from apps.email.models import Email
from apps.product.models import Product
from apps.sibt.models import SIBTInstance

from util.urihandler import URIHandler


class SkypeCallTestingService(URIHandler):
    def get(self):
        instance = SIBTInstance.get('fb0b475f4e984f87')
        Email.SIBTVoteCompletion(instance=instance,
                                 product=Product.get(instance.products[0]))