#!/usr/bin/env python

__author__ = "Willet, Inc."
__copyright__ = "Copyright 2012, Willet, Inc"

import hashlib
import datetime

from util.consts import URL
from util.helpers import url
from util.urihandler import URIHandler


class SIBTShuuemuraServeScript(URIHandler):
    """Does everything SIBTServeScript does."""
    def get(self):
        """Does everything SIBTServeScript does."""

        security_id = hashlib.sha224("Nobody inspects the spammish repetition").hexdigest()

        self.redirect("%s%s?%s&sid=%s" % (URL,
                                   url('SIBTServeScript'),
                                   self.request.query_string,
                                   security_id),
                      permanent=True)
        return