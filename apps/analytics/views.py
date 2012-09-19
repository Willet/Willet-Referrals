#!/usr/bin/env python

from google.appengine.ext.webapp import template

from apps.client.shopify.models import ClientShopify
from apps.user.models import User

from util.consts import SECURE_URL
from util.urihandler import URIHandler

import os

class TrackingJSLoader(URIHandler):
    tsx = ['leadspeaker']
    ttx = ['shopify']

    def get(self):
        user = User.get_by_cookie(self)

        # Grab shop URL from params
        shop_url = self.request.get('shop')
        if shop_url[:7] != 'http://':
            shop_url = 'http://%s' % shop_url

        tracking_system = self.request.get('ts')
        tracking_type = self.request.get('tt')

        # not sure what's being asked of us; return nothing
        if tracking_system not in self.tsx or tracking_type not in self.ttx:
            return

        # Grab appropriate client based on the request
        if tracking_type == 'shopify':
            client = ClientShopify.get_by_url(shop_url)

        # Grab all template values
        template_values = {
                'SECURE_URL' : SECURE_URL,
        }

        if user:
            template_values.update({'user': user})

        if client:
            template_values.update({'client': client})

        # Finally, render the JS!
        path = os.path.join('templates/analytics', '%s_%s.js' % (tracking_system, tracking_type))

        self.response.headers.add_header('P3P', 'CP="NOI DSP LAW DEVo IVDo OUR STP ONL PRE NAV"')
        self.response.headers['Content-Type'] = 'text/html; charset=utf-8'
        self.response.out.write(template.render(path, template_values))

        return