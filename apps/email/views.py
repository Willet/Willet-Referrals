#!/usr/bin/env python

__author__ = "Willet Inc."
__copyright__ = "Copyright 2012, The Willet Corporation"

from apps.email.models import Email
from apps.product.models import Product
from apps.sibt.models import SIBTInstance

from util.urihandler import URIHandler


class SkypeCallTestingService(URIHandler):
    def get(self):
        instance = SIBTInstance.get('c2039b05df1841b9')
        Email.SIBTVoteCompletion(instance=instance,
                                 product=Product.get(instance.products[0]))