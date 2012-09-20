#!/usr/bin/env python

from util.consts import SECURE_URL, P3P_HEADER
from util.shopify_helpers import get_shopify_url
from util.urihandler import URIHandler

from google.appengine.ext.webapp import template

import os


class TrackingJSLoader(URIHandler):
    """When requested shares an appropriate tracking js file.

    @TODO: Ideally need to phase this out and serve tracking files as fully static.
    """

    # currently supported tracking "systems" and "types"
    tsx = ['leadspeaker']
    ttx = ['shopify']

    def get(self):
        # Grab shop URL from params
        shop_hostname = self.request.get('shop')

        tracking_system = self.request.get('ts')
        tracking_type = self.request.get('tt')

        # we set this via shopify store admin for the Thank You page
        landing_site = self.request.get('landing_site')

        # not sure what's being asked of us; return nothing
        if tracking_system not in self.tsx or tracking_type not in self.ttx:
            return

        # Grab all template values
        template_values = {
            'SECURE_URL': SECURE_URL,
            'shop_hostname': shop_hostname
        }

        if landing_site:
            template_values.update({'landing_site': landing_site})

        # Finally, render the JS!
        path = os.path.join('templates/analytics', '%s_%s.js' %
                            (tracking_system, tracking_type))

        self.response.headers.add_header('P3P', P3P_HEADER)
        self.response.headers['Content-Type'] = 'text/html; charset=utf-8'
        self.response.out.write(template.render(path, template_values))

        return