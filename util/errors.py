#!/usr/bin/python

# Exceptions

__author__ = "Willet, Inc."
__copyright__ = "Copyright 2012, Willet, Inc"

import logging


class RemoteError(Exception):
    """ Exception raised when a HTTP fetch returns fails or returns an unexpected results"""

    def __init__(self, HTTP_status_code, HTTP_status_msg, description):
        self.status = HTTP_status_code
        self.name = HTTP_status_msg
        self.description = description

    def __str__(self):
        return "%s %s: %s" % (self.status, self.name, self.description)

class ShopifyAPIError(RemoteError):
    """ A more descriptive exception for Shopify """
    pass

class BillingError(Exception):
    """ Exception raised when a billing API request fails or returns an unexpected result"""

    def __init__(self, message, data=None):
        self.message = message
        self.data = data

    def __str__(self):
        return "%s\ndata: %r" % (self.message, self.data)

class ShopifyBillingError(BillingError):
    """ A more descriptive exception for Shopify """
    pass


def deprecated(fn):
    """DeprecationWarning decorator."""
    def wrapped(*args, **kwargs):
        raise DeprecationWarning("Call to deprecated function " % fn.__name__)
    return wrapped


def will_be_deprecated(fn):
    """PendingDeprecationWarning decorator.

    Function will still work, but will emit an error log."""
    def wrapped(*args, **kwargs):
        try:
            raise PendingDeprecationWarning("Call to deprecated "
                                            "function " % fn.__name__)
        except PendingDeprecationWarning, err:
            logging.error('%s' % err, exc_info=True)
    return wrapped