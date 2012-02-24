#!/usr/bin/python

# Exceptions

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2012, Willet, Inc"


class RemoteError(Exception):
    """ Exception raised when a HTTP fetch returns fails or returns an unexpected results"""

    def __init__(self, HTTP_status_code, HTTP_status_msg, description):
        self.status = HTTP_status_code
        self.name = HTTP_status_msg
        self.description = description
    
    def __str__(self):
        return "%s %s: %s" % (self.status, self.name, self.description)

class BillingError(Exception):
    """ Exception raised when a billing API request fails or returns an unexpected result"""

    def __init__(self, message, data):
        self.message = message
        self.data = data

    def __str__(self):
        return "%s\ndata: %r" % (self.message, self.data)