#!/usr/bin/env python

__author__ = "Willet, Inc."
__copyright__ = "Copyright 2011, Willet, Inc"

import logging
import os

from google.appengine.ext.webapp import template

from apps.app.models import App
from apps.client.shopify.models import ClientShopify
from apps.order.shopify.models import OrderShopify
from apps.user.models import User

from util.consts import SECURE_URL
from util.urihandler import URIHandler


class OrderJSLoader(URIHandler):
    """When requested serves a plugin that will contain various functionality
       for sharing information about a purchase just made by one of our clients
    """
    def get(self):
        user = User.get_by_cookie(self)

        # Grab shop URL from params
        shop_url = self.request.get('shop')
        if shop_url[:7] != 'http://':
            shop_url = 'http://%s' % shop_url

        # Grab Shopify Store
        client = ClientShopify.get_by_url(shop_url)

        # Grab all template values
        template_values = {
                'SECURE_URL' : SECURE_URL,
                'user'       : user,
                'client'     : client
        }

        # Finally, render the JS!
        path = os.path.join('order', 'order.js')

        self.response.headers.add_header('P3P', 'CP="NOI DSP LAW DEVo IVDo OUR STP ONL PRE NAV"')
        self.response.headers['Content-Type'] = 'text/html; charset=utf-8'
        self.response.out.write(template.render(path, template_values))

        return