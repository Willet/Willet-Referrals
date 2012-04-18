#!/usr/bin/env python

__author__ = "Willet, Inc."
__copyright__ = "Copyright 2012, Willet, Inc"

import datetime
import logging
import os

from datetime import datetime, timedelta
from google.appengine.ext.webapp import template

from apps.sibt.shopify.models import SIBTShopify
from apps.user.models import User
from apps.wosib.actions import WOSIBVoteAction
from apps.wosib.models import WOSIBInstance
from apps.wosib.shopify.models import WOSIBShopify

from util.consts import *
from util.helpers import get_target_url
from util.shopify_helpers import get_shopify_url
from util.urihandler import URIHandler

class WOSIBShopifyServeScript(URIHandler):
    """Renders a javascript that shows the WOSIB button."""
    def get(self):
        """Renders a javascript that shows the WOSIB button.

        Required parameters:
        - store_url (the store domain)
        """
        app_css = ''
        asker_name = None
        asker_pic = None
        client = None
        event = 'WOSIBShowingButton'
        has_voted = False
        instance = None
        instance_uuid = ''
        is_asker = False
        link = None
        referrer = self.request.headers.get('REFERER')
        share_url = None
        show_votes = False
        store_domain = ''
        target = ''
        votes_count = 0

        shop_url = get_shopify_url(self.request.get('store_url'))
        if not shop_url:  # backup (most probably hit)
            shop_url = get_target_url(referrer)  # probably ok
        logging.debug("shop_url = %s" % shop_url)

        # use the SIBT's CSS and client
        app_sibt = SIBTShopify.get_by_store_url(shop_url)
        app = WOSIBShopify.get_by_store_url(shop_url)

        # Try to find an instance for this { url, user }
        logging.debug("trying app = %s" % app)
        if not app:
            logging.error("no app for %s */" % shop_url)
            self.response.out.write("/* no app for %s */" % shop_url)
            return

        target = get_target_url(referrer)
        user = User.get_or_create_by_cookie(self, app)

        # WOSIBInstances record the user. Find the user's most recent instance.
        logging.info('trying to get instance for user: %r' % user)
        instance = WOSIBInstance.get_by_user_and_app(user, app)

        if not instance:
            logging.info('no instance available')
        else:
            """If we have an instance, figure out if

            a) Is User asker?
            b) Has this User voted?
            """
            instance_uuid = instance.uuid

            # number of votes, not the votes objects.
            votes_count = instance.get_votes_count() or 0
            logging.info("votes_count = %s" % votes_count)

            asker_name = instance.asker.get_first_name()
            asker_pic = instance.asker.get_attr('pic')
            show_votes = True

            try:
                asker_name = asker_name.split(' ')[0]
                if not asker_name:
                    asker_name = 'I'
            except:
                logging.warn('error splitting the asker name')

            is_asker = bool(instance.asker.key() == user.key()) 
            if not is_asker:
                vote_action = WOSIBVoteAction.get_by_app_and_instance_and_user(app, instance, user)
                has_voted = bool(vote_action != None)
                logging.info('not asker; has_voted = %r' % has_voted)

            try:
                if not link: 
                    link = instance.link
                share_url = link.get_willt_url()
            except Exception, e:
                logging.error("could not get share_url: %s" % e, exc_info=True)

        if not user.is_admin():
            cta_button_text = "Need advice? Ask your friends!"
        else:
            cta_button_text = "ADMIN: Unsure? Ask your friends!"

        try:
            app_css = app_sibt.get_css()
        except AttributeError:
            app_css = ''

        try:
            client = app_sibt.client
            store_domain = client.domain
        except AttributeError:  # app is not installed. fake a no-app.
            logging.error("no app for %s */" % shop_url)
            self.response.out.write("/* no app for %s */" % shop_url)
            return

        # determine whether to show the button thingy.
        # code below makes button show only if vote was started less than 1 day ago.
        has_results = False
        if votes_count:
            time_diff = datetime.now() - instance.created
            if time_diff <= timedelta(days=1):
                has_results = True

        # Grab all template values
        template_values = {
            'URL': URL,
            'app': app,
            'app_css': app_css,
            'instance': instance,
            'store_domain': store_domain,
            'store_id': self.request.get('store_id'),
            'user': user,
            'instance_uuid': instance_uuid,
            'stylesheet': '../../plugin/templates/css/colorbox.css',
            'evnt': event,
            'cta_button_text': cta_button_text,
            'shop_url': shop_url,
            # tells client JS if the user had created an instance
            'has_results': 'true' if has_results else 'false',
        }

        path = os.path.join('apps/wosib/templates/', 'wosib.js')
        self.response.headers.add_header('P3P', P3P_HEADER)
        self.response.headers['Content-Type'] = 'application/javascript'
        self.response.out.write(template.render(path, template_values))

        return