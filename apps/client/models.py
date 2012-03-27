#!/usr/bin/python

# client models
# data models for our clients and associated methods

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc"

import hashlib, logging, urllib, urllib2

from datetime               import datetime
from decimal                import *
from django.utils           import simplejson as json
from google.appengine.api   import memcache
from google.appengine.api   import urlfetch
from google.appengine.api   import taskqueue
from google.appengine.ext   import db
from google.appengine.ext.db import polymodel

from util.consts            import *
from util.mailchimp         import MailChimp
from util.model             import Model
from util.helpers           import generate_uuid


class Client(Model, polymodel.PolyModel):
    """A Client or the website"""
    creation_time = db.DateTimeProperty(auto_now_add = True, indexed = False)
    email         = db.StringProperty  (indexed=True)

    def __init__(self, *args, **kwargs):
        self._memcache_key = hashlib.md5(kwargs['email']).hexdigest() if 'email' in kwargs else None 
        super(Client, self).__init__(*args, **kwargs)
    
    @staticmethod
    def _get_from_datastore(google_user):
        """Datastore retrieval using memcache_key"""
        return db.Query(Client).filter('uuid =', google_user).get()

    # Retrievers ------------------------------------------------------------------------------------
    @classmethod
    def get_by_email(cls, email):
        client = cls.get(hashlib.md5(email).hexdigest())
        if client:
            return client
        return cls.all().filter('email =', email).get()

    @classmethod
    def get_by_uuid(uuid):
        return cls.all().filter('uuid =', uuid).get()

    # Mailing list methods --------------------------------------------------------------------------
    def subscribe_to_mailing_list(self, list_name='', list_id=None):
        """ Add client to MailChimp
             MailChimp API Docs: http://apidocs.mailchimp.com/api/1.3/listsubscribe.func.php
        """
        resp = {}
        first_name, last_name = '',''
        name = self.merchant.get_full_name()
        try:
            first_name, last_name = name.split(' ')[0], (' ').join(name.split(' ')[1:])
        except IndexError:
            first_name, last_name = name, ''

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
                                send_welcome=False )
                # Response can be:
                #     <bool> True / False (unsubscribe worked, didn't work)
                #     <dict> error + message
            except Exception, e:
                # This is bad form to except everything, but we really can't have a failure on install
                logging.error('Subscribe %s from %s FAILED: %r' % (self.email, list_name, e), exc_info=True)
            else:
                try:
                    if 'error' in resp:
                        logging.error('Subscribe %s from %s FAILED: %r' % (self.email, list_name, resp))
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
                                send_goodbye=False )
                # Response can be:
                #     <bool> True / False (unsubscribe worked, didn't work)
                #     <dict> error + message
            except Exception, e:
                # This is bad form to except everything, but we really can't have a failure on uninstall
                logging.error('Unsubscribe %s from %s FAILED: %r' % (self.email, list_name, e), exc_info=True)
            else:
                try:
                    if 'error' in resp:
                        logging.error('Unsubscribe %s from %s FAILED: %r' % (self.email, list_name, resp))
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
