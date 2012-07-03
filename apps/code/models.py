#!/usr/bin/env python

"""Code and DiscountCode classes."""

__author__ = "Willet, Inc."
__copyright__ = "Copyright 2012, Willet, Inc"

import datetime
import logging
import random

from google.appengine.ext import db

from apps.client.models import Client
from apps.user.models import User

from util.helpers import generate_uuid
from util.model import Model

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
        kwargs['key_name'] = kwargs.get('uuid')

        code_obj = cls(**kwargs)
        code_obj.put()

        return code_obj

    @classmethod
    def get_or_create(cls, **kwargs):
        """Looks up by kwargs[uuid], or creates one using the rest of kwargs
        if none found.
        """
        code = cls.get(kwargs.get('uuid', ''))
        if code:
            return code

        code = cls.create(**kwargs)
        return code

    @classmethod
    def get_by_code(cls, code):
        """Retrieve a Code object by its actual code string.

        Subclass-specific filtering functions may be available.
        """
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
    # because of who we are, a code is used whenever we give it out,
    # not whenever the User receives a discount.
    used = db.BooleanProperty(default=False, indexed=True)

    # used for checking if a user got multiple discount codes from the same
    # client.
    user = db.ReferenceProperty(User, required=False,
                                collection_name='user_discount_codes')

    # rebated is True if user got a discount from it.
    # currently used and handled by nobody.
    rebated = db.BooleanProperty(default=False, indexed=False)

    def __init__(self, *args, **kwargs):
        super(DiscountCode, self).__init__(*args, **kwargs)

    def _validate_self(self):
        if not self.client:
            raise ValueError('Cannot save a discount code without a client')
        if self.rebated and not self.used:
            raise ValueError('wtf? Must use discount code to rebate it')
        return True

    @classmethod
    def generate_code(cls):
        """for types of discount code where we get our hands on the
        generating algorithm, this method can be overwritten.

        It is not used by Shu Uemura because they just give us the codes.
        """
        return generate_uuid(16)

    @classmethod
    def get_by_client_and_code(cls, code, client, used=False, **kwargs):
        """In the case that multiple clients have different discount
        codes of the same value (e.g. SAVE50), then we can filter by client.

        Function gets the first code available and exits.

        By default, this returns only unused codes.
        """

        logging.debug('getting discount code '
                      'using params %r %r %r' % (code, client, used))
        return cls.all()\
                  .filter('code =', code)\
                  .filter('client =', client)\
                  .filter('used =', used)\
                  .get()

    @classmethod
    def get_or_create(cls, **kwargs):
        """Looks up by kwargs[uuid], or any other method that this subclass
        understands. Otherwise, it creates one using the rest of kwargs
        if none found.
        """
        code = cls.get(kwargs.get('uuid'))
        if code:
            return code

        logging.debug('code not found by uuid')
        # assuming you got the params right...
        code = cls.get_by_client_and_code(**kwargs)
        if code:
            return code

        logging.debug('code not found by client and code! creating.')
        code = cls.create(**kwargs)
        return code

    @classmethod
    def get_by_client_at_random(cls, client):
        """Return a random, non-expired code from a client.

        Note that this will cost extra reads.
        """
        all_tickets = cls.all()\
                         .filter('client =', client)\
                         .filter('used =', False)
        try:
            get_ticket_number = random.randint(0, all_tickets.count())
            if get_ticket_number:  # if it's not 0
                return all_tickets.get(offset=get_ticket_number)
        except ValueError, err:
            logging.warn('ran out of discount codes?! %s' % err, exc_info=True)
            return None

    def use_code(self, user=None):
        """Not very useful now; marks a DiscountCode as used."""
        self.used = True
        self.user = user
        self.put()

    def unuse_code(self):
        """Not very useful now; marks a DiscountCode as unused."""
        self.used = False
        self.user = None
        self.put()

    def is_expired(self):
        """If it is used, it also counts as expired."""
        return bool(datetime.datetime.now() > self.expiry_date) or self.used