#!/usr/bin/env python

import datetime
import logging
import random

from google.appengine.api import memcache
from google.appengine.ext import db
from apps.client.models import Client

from util.helpers import generate_uuid
from util.model import Model
from util.shopify_helpers import get_url_variants


class Code(Model):
    """Superclass about a code.

    It can be any code. It can have any association.
    Subclasses define its purpose and use.
    """
    code = db.StringProperty(indexed=True, required=True)

    _memcache_fields = ['code']

    def __init__(self, *args, **kwargs):
        self._memcache_key = kwargs['uuid'] if 'uuid' in kwargs else None
        super(Code, self).__init__(*args, **kwargs)

    def _validate_self(self):
        return True

    @classmethod
    def _get_memcache_key(cls, uuid):
        """."""
        return '%s:%s' % (cls.__name__.lower(), unicode(uuid))

    @classmethod
    def _get_from_datastore(cls, uuid):
        """Datastore retrieval using memcache_key"""
        return db.Query(cls).filter('uuid =', uuid).get()

    @classmethod
    def create(cls, **kwargs):
        """Creates a code in the datastore using kwargs.

        Subclasses will have different field requirements.

        It will raise its own error if
        - you do not supply the appropriate fields, or
        - you give it too many fields.
        """
        if not kwargs.get('code', ''):
            raise AttributeError("Must have code")

        kwargs['uuid'] = kwargs.get('uuid', generate_uuid(16))

        code_obj = cls(**kwargs)
        code_obj.put()

        return code_obj

    @classmethod
    def get_or_create(cls, **kwargs):
        """Looks up by kwargs[uuid], or creates one using the rest of kwargs
        if none found.
        """
        code = Code.get(kwargs.get('uuid', ''))
        if code:
            return code

        code = cls.create(**kwargs)
        return code

    @classmethod
    def get_by_code(cls, code):
        return cls.all().filter('code =', code).get()


class DiscountCode(Code):
    """Stores information about a discount code.

    Codes can have only one client (the company who gave us the code).
    """
    # so, you can use Client.discount_codes to get them.
    client = db.ReferenceProperty(Client, required=True,
                                  collection_name='discount_codes')

    # if not set, this code is infinitely valid.
    # default value appears as <null> in DB viewer.
    expiry_date = db.DateTimeProperty(required=False)

    # whether this discount code is used.
    used = db.BooleanProperty(default=False, indexed=True)

    def __init__(self, *args, **kwargs):
        super(DiscountCode, self).__init__(*args, **kwargs)

    def _validate_self(self):
        if not self.client:
            raise ValueError('Cannot save a discount code without a client')

    @classmethod
    def get_by_client_and_code(cls, code, client, used=False):
        """In the case that multiple clients have different discount
        codes of the same value (e.g. SAVE50), then we can filter by client.

        By default, this returns only unused codes.
        """
        return cls.all()\
                  .filter('code =', code)\
                  .filter('client =', client)\
                  .filter('used =', used)\
                  .get()

    @classmethod
    def get_by_client_at_random(cls, code, client):
        """Return a random, non-expired code from a client.

        Note that this will cost extra reads.
        """
        all_tickets = cls.all()\
                         .filter('client =', client)\
                         .filter('used =', False)
        get_ticket_number = random.randint(0, all_tickets.count() - 1)
        if get_ticket_number:  # if it's not 0
            return all_tickets.get(offset=get_ticket_number)

        logging.warn('ran out of discount codes?!')
        return None

    def use_code(self):
        """Not very useful now; marks a DiscountCode as used."""
        self.used = True
        self.put()

    def unuse_code(self):
        """Not very useful now; marks a DiscountCode as unused."""
        self.used = False
        self.put()

    def is_expired(self):
        """If it is used, it also counts as expired."""
        if datetime.datetime.now() > self.expiry_date:
            return True  # yes, it is expired

        if self.used:
            return True

        # I guess it's still good
        return False