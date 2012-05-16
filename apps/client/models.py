#!/usr/bin/python

"""Client models: data models for our clients and associated methods."""

__author__ = "Willet, Inc."
__copyright__ = "Copyright 2012, Willet, Inc"

import logging

from decimal import *
from google.appengine.ext import db
from google.appengine.ext.db import polymodel

from apps.user.models import *
from util.consts import *
from util.mailchimp import MailChimp
from util.model import Model
from util.helpers import generate_uuid
from util.shopify_helpers import get_url_variants


class Client(Model, polymodel.PolyModel):
    """A Client of the website.

    Client models can be for any platform - use ClientShopify to easily
    authenticate with Shopify shops.
    """
    creation_time = db.DateTimeProperty(auto_now_add=True, indexed=False)
    email = db.StringProperty(indexed=True)

    merchant = MemcacheReferenceProperty(db.Model, collection_name="stores")
    # Store properties
    name = db.StringProperty(indexed=False)
    url = db.LinkProperty(indexed=True)
    domain = db.LinkProperty(indexed=True)

    # False, unless this client has a private deal with us.
    vendor = db.BooleanProperty(required=False, default=False)

    _memcache_fields = ['domain', 'email', 'url']

    def __init__(self, *args, **kwargs):
        self._memcache_key = None
        if 'email' in kwargs:
            self._memcache_key = Client.build_secondary_key(kwargs['email'])
        super(Client, self).__init__(*args, **kwargs)

    def _validate_self(self):
        return True

    @staticmethod
    def _get_from_datastore(google_user):
        """Datastore retrieval using memcache_key"""
        return db.Query(Client).filter('uuid =', google_user).get()

    @staticmethod
    def create(url, request_handler, user):
        """ Creates a Store (Client).
            This process requires a user (merchant) to be associated with the
            client. Code must supply a user object for Client to be created.
        """

        uuid = Client.build_secondary_key(url)

        if not user:
            raise ValueError("User is missing")

        try:
            user_name = user.full_name
            user_email = user.emails[0].address  # emails is a back-reference
        except AttributeError:
            msg = "User supplied must have at least name and one email address"
            logging.error(msg, exc_info=True)
            raise AttributeError(msg)  # can't really skip that

        # Now, make the store
        client = Client(key_name=uuid,
                        uuid=uuid,
                        name=user_name,
                        email=user_email,
                        url=url,
                        domain=url,  # I really don't see the difference.
                        merchant=user,
                        vendor=False)
        client.put()

        return client

    @staticmethod
    def get_or_create(url, request_handler=None, user=None):
        client = Client.get_by_url(url)
        if not client:
            client = Client.create(url=url,
                                   request_handler=request_handler,
                                   user=user)
        return client

    # Retrievers --------------------------------------------------------------
    @classmethod
    def get_by_url(cls, url):
        if not url:
            return None

        www_url = url

        (url, www_url) = get_url_variants(url, keep_path=False)

        res = cls.get(url) # wild try w/ memcache?
        if res:
            return res

        res = cls.get(www_url) # wild try w/ memcache?
        if res:
            return res

        # memcache miss?
        res = db.Query(cls).filter('url IN', [url, www_url]).get()
        if res:
            return res
        # domain is the less-authoritative field, but try it anyway
        return db.Query(cls).filter('domain IN', [url, www_url]).get()

    @classmethod
    def get_by_email(cls, email):
        if not email:
            return None

        client = cls.get(email)
        if client:
            return client
        return cls.all().filter('email =', email).get()

    @classmethod
    def get_by_uuid(cls, uuid):
        return cls.all().filter('uuid =', uuid).get()

    # Mailing list methods ----------------------------------------------------
    def subscribe_to_mailing_list(self, list_name='', list_id=None):
        """Add client to MailChimp.

        MailChimp API Docs: http://apidocs.mailchimp.com/api/1.3/listsubscribe.func.php
        """
        resp = {}
        first_name, last_name = '',''
        name = self.merchant.get_full_name()
        if name:
            try:
                first_name, last_name = name.split(' ')[0], (' ').join(name.split(' ')[1:])
            except IndexError: # Only contains a first name
                first_name, last_name = name, ''
        else:
            first_name, last_name = 'Store Owner', ''

        if list_id:
            try:
                resp = MailChimp(MAILCHIMP_API_KEY).listSubscribe(
                                id=list_id,
                                email_address=self.email,
                                merge_vars=({ 'FNAME': first_name,
                                              'LNAME': last_name,
                                              'STORENAME': self.name,
                                              'STOREURL': self.url }),
                                double_optin=False,
                                send_welcome=False)
                # Response can be:
                #     <bool> True / False (unsubscribe worked, didn't work)
                #     <dict> error + message
            except Exception, e:
                # This is bad form to except everything, but we really can't have a failure on install
                logging.error('Subscribe %s from %s FAILED: %r' % (self.email, list_name, e), exc_info=True)
            else:
                try:
                    if 'error' in resp:
                        logging.warning('Subscribe %s from %s FAILED: %r' % (self.email, list_name, resp))
                except TypeError:
                    # thrown when results is not iterable (eg bool)
                    logging.info('Subscribed %s from %s OK: %r' % (self.email, list_name, resp))
        return

    def unsubscribe_from_mailing_list(self, list_name='', list_id=None):
        """ Remove client from MailChimp list
            MailChimp API Docs: http://apidocs.mailchimp.com/api/1.3/listunsubscribe.func.php
        """
        resp = {}
        if list_id:
            try:
                resp = MailChimp(MAILCHIMP_API_KEY).listUnsubscribe(
                                id=list_id,
                                email_address=self.email,
                                delete_member=False,
                                send_notify=False,
                                send_goodbye=False)
                # Response can be:
                #     <bool> True / False (unsubscribe worked, didn't work)
                #     <dict> error + message
            except Exception, e:
                # This is bad form to except everything, but we really can't have a failure on uninstall
                logging.error('Unsubscribe %s from %s FAILED: %r' % (self.email, list_name, e), exc_info=True)
            else:
                try:
                    if 'error' in resp:
                        logging.warning('Unsubscribe %s from %s FAILED: %r' % (self.email, list_name, resp))
                except TypeError:
                    # thrown when results is not iterable (eg bool)
                    logging.info('Unsubscribed %s from %s OK: %r' % (self.email, list_name, resp))
        return


# TODO delete these deprecated functions after April 26, 2012 (1 month warning)
def get_client_by_email(email):
    logging.error('Deprecated function get_client_by_email should be replaced by Client.get_by_email')
    return Client.get_by_email(email)

def get_client_by_uuid(uuid):
    logging.error('Deprecated function get_client_by_uuid should be replaced by Client.get_by_uuid')
    return Client.get_by_uuid(uuid)
