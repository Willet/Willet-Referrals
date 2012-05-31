#!/usr/bin/python

"""Use the Charge Model for storing when we bill someone.

We will call it a Charge.
Future "fancier" developers may implement class-specific charges
(e.g. recurring charges)
"""

__author__ = "Willet, Inc."
__copyright__ = "Copyright 2012, Willet, Inc"

import logging

from google.appengine.ext import db
from google.appengine.ext.db import polymodel

from util.helpers import generate_uuid
from util.model import Model

class Charge(Model, polymodel.PolyModel):
    """Model for storing any charge.

    This class does not issue charges. It merely records the fact that we had.

    You can put custom fields in this too (with polymodel)
    """

    # Datetime when this model was put into the DB
    created = db.DateTimeProperty(auto_now_add=True)

    # Datetime when this model was last modified
    modified = db.DateTimeProperty(auto_now=True)

    # Who are you charging? (implies that you can only charge clients)
    client = db.ReferenceProperty(db.Model, collection_name='client_charges')

    # For what are you charging? (not a required field if not charging an app)
    app = db.ReferenceProperty(db.Model, collection_name='app_charges')

    # The charge, in Canadian Dollars. Controllers are responsible for
    # converting the currency-value *at the time of saving*.
    # charging for less than $0.01 is meaningless, and will be barred from
    # saving.
    value = db.FloatProperty(required=True, indexed=False, default=0.01)

    # a field for making notes (like the memo area on a cheque)
    notes = db.StringProperty(required=False, indexed=False, default='')

    def __init__(self, *args, **kwargs):
        self._memcache_key = kwargs['uuid'] if 'uuid' in kwargs else None
        super(Charge, self).__init__(*args, **kwargs)

    def _validate_self(self):
        """Setup validation or autocorrection."""
        if self.value < 0.01:
            raise ValueError('Invalid charge value of %f' % self.value)
        return True

    @classmethod
    def _get_from_datastore(cls, uuid):
        """Datastore retrieval using memcache_key"""
        return cls.all().filter('uuid =', uuid).get()

    @classmethod
    def create(cls, **kwargs):
        """Creates a Charge in the datastore using kwargs.

        Subclasses will have different field requirements.

        It will raise its own error if
        - you do not supply the appropriate fields, or
        - you give it too many fields.
        """
        if not kwargs.get('value', 0.0) or kwargs['value'] < 0.01:
            raise AttributeError("Cannot issue free or negative charges")

        kwargs['uuid'] = kwargs.get('uuid', generate_uuid(16))
        kwargs['key_name'] = kwargs.get('uuid')

        chrg_obj = cls(**kwargs)
        chrg_obj.put()

        return chrg_obj

    @classmethod
    def get_or_create(cls, **kwargs):
        """Looks up by kwargs[uuid], or creates one using the rest of kwargs
        if none found.
        """
        chrg = cls.get(kwargs.get('uuid', ''))
        if chrg:
            return chrg

        chrg = cls.create(**kwargs)
        return chrg

    @classmethod
    def get_by_client(cls, client):
        """Ignoring memcache, fetch all charges by this client. Unsorted."""
        # return cls.all().filter('client =', client).get()
        return client.client_charges