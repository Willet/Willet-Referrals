#!/usr/bin/env python

__author__ = "Willet, Inc."
__copyright__ = "Copyright 2012, Willet, Inc"

import logging

from django.utils import simplejson as json

from apps.client.models import Client

from util.urihandler import URIHandler


class ClientJSONDynamicLoader(URIHandler):
    """Return a JSON object for an app given a client_uuid if found,
    HTTP 404 otherwise.
    """
    def get(self):
        """See class docstring."""
        client = Client.get(self.request.get('client_uuid'))
        if not client:
            self.error(404)
            return

        self.response.out.write(json.dumps({
            'uuid': client.uuid,
            'url': getattr(client, 'url', getattr(client, 'domain', '')),
            'name': getattr(client, 'name', getattr(client, 'store_name', '')),
        }))