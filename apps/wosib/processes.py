#!/usr/bin/env python

__author__ = "Willet, Inc."
__copyright__ = "Copyright 2012, Willet, Inc"

import hashlib
import random

from datetime import datetime
from django.utils import simplejson as json
from urlparse import urlunsplit

from google.appengine.api import taskqueue
from google.appengine.ext import db

from apps.app.models import App
from apps.email.models import Email
from apps.link.models import Link
from apps.product.models import Product
from apps.user.models import User
from apps.user.models import User
from apps.wosib.actions import *
from apps.wosib.models import WOSIB, WOSIBInstance
from apps.wosib.shopify.models import WOSIBShopify
from apps.wosib.models import PartialWOSIBInstance

from util.consts import *
from util.helpers import url
from util.urihandler import URIHandler


class WOSIBDoVote(URIHandler):
    def post(self):
        self.redirect("%s%s?%s" % (URL,
                            url('DoVote'),
                            self.request.query_string),
                permanent=True)


class GetExpiredWOSIBInstances(URIHandler):
    def post(self):
        return self.get()

    def get(self):
        """Gets a list of WOSIB instances to be expired and emails to be sent"""
        right_now = datetime.datetime.now()
        expired_instances = WOSIBInstance.all()\
                .filter('is_live =', True)\
                .filter('end_datetime <=', right_now)

        for instance in expired_instances:
            taskqueue.add(
                url = url('RemoveExpiredWOSIBInstance'),
                params = {
                    'instance_uuid': instance.uuid
                }
            )
        logging.info('expiring %d instances' % expired_instances.count())


class RemoveExpiredWOSIBInstance(URIHandler):
    def post(self):
        return self.get()

    def get(self):
        """Updates the WOSIB instance in a transaction and then emails the user"""
        def txn(instance):
            instance.is_live = False
            instance.put()
            return instance

        instance = WOSIBInstance.get(self.request.get('instance_uuid'))
        if instance != None:
            result_instance = db.run_in_transaction(txn, instance)
            email = instance.asker.get_attr('email')
            Email.WOSIBVoteCompletion(result_instance)
        else:
            logging.error("could not get instance for uuid %s" % instance_uuid)
        logging.info('done expiring')


class StartPartialWOSIBInstance(URIHandler):
    def get (self):
        self.post()

    def post(self):
        app = App.get(self.request.get('app_uuid'))
        link = Link.get_by_code(self.request.get('willt_code'))

        products = self.request.get('product_uuids')
        logging.info ('products = %s' % products)
        user = User.get(self.request.get('user_uuid'))
        PartialWOSIBInstance.create(user, app, link, products.split(','))


class StartWOSIBInstance(URIHandler):
    def post(self):
        app = App.get (self.request.get('app_uuid'))
        link = Link.get_by_code(self.request.get('willt_code')) # this is crazy
        products = self.request.get('product_uuids')
        logging.info ('products = %s' % products)
        user = User.get(self.request.get('user_uuid'))

        logging.info("Starting WOSIB instance for %s" % link.target_url)

        # defaults
        response = {
            'success': False,
            'data': {
                'instance_uuid': None,
                'message': None
            }
        }

        try:
            # Make the Instance! "None" sets vote time to 6 hrs
            instance = app.create_instance(user, None, link)

            response['success'] = True
            response['data']['instance_uuid'] = instance.uuid
        except Exception,e:
            response['data']['message'] = str(e)
            logging.error('we had an error creating the instnace', exc_info=True)

        self.response.out.write(json.dumps(response))


class StartWOSIBAnalytics(URIHandler):
    # StartWOSIBAnalytics will eventually serve the same purpose as StartSIBTAnalytics
    # in SIBT: tally WOSIB actions.
    def get(self):
        # TODO: WOSIB Analytics
        self.response.out.write("No analytics yet")


class SendWOSIBFriendAsks(URIHandler):
    """ Sends messages to email & FB friends

    Expected inputs:
        friends: JSON-encoded <Array> [ <array> [ <string> type, <string> name, <string> identifier ]
        asker: JSON-encoded <array> [<string> name, <string> email_address [, <string> picture_url ]]
        msg: <string> message
        default_msg: <string> message before user edited it
        app_uuid: <string> a WOSIB app uuid
        willt_code: <string> willt_code corresponding to a parital WOSIB instance
        user_uuid: <string> a <User> uuid
        fb_access_token: <string> a Facebook API access token for this user
        fb_id: <string> a Facebook user id for this user

    Expected output (JSON-encoded):
        success: <Boolean> at least some friends were successfully contacted
        data: <Dict>
            message: <String> description of outcome
            warnings: <Array> [ <string> explanation of any incompleted friend asks ]
    """
    def get (self):
        self.post()

    def post(self):
        self.redirect("%s?%s" % (url('SendFriendAsks'),
                                 self.request.query_string))
        return