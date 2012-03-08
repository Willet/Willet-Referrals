#!/usr/bin/python

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2012, Willet, Inc"

from google.appengine.ext import db
from google.appengine.api import memcache

NUM_VOTE_SHARDS = 15

# ------------------------------------------------------------------------------
# VoteCounter Class Definition ------------------------------------------------
# ------------------------------------------------------------------------------

class VoteCounter(db.Model):
    """Sharded counter for voting counts"""

    instance_uuid = db.StringProperty(indexed=True, required=True)
    yesses        = db.IntegerProperty(indexed=False, required=True, default=0)
    nos           = db.IntegerProperty(indexed=False, required=True, default=0)
