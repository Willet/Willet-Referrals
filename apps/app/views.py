#!/usr/bin/env python

__author__ = "Willet, Inc."
__copyright__ = "Copyright 2012, Willet, Inc"

import logging

from django.utils import simplejson as json

from apps.app.models import App
from apps.client.models import Client

from util.urihandler import URIHandler


class DoDeleteApp(URIHandler):
    """Why is this thing in views.py? TODO move to processes.py."""
    def post(self):
        client = self.get_client()
        app_uuid = self.request.get('app_uuid')

        logging.info('app id: %s' % app_uuid)
        app = App.get(app_uuid)
        if app.client.key() == client.key():
            logging.info('deelting')
            app.delete()

        self.redirect('/client/account')


class AppJSONDynamicLoader(URIHandler):
    """Return a JSON object for an app given a app_uuid if found,
    a JSON object for a list of apps given a client_uuid if found,
    HTTP 404 otherwise.
    """
    def get(self):
        """See class docstring."""
        app = App.get(self.request.get('app_uuid'))
        if app:
            self.response.out.write(json.dumps({
                'uuid': app.uuid,
                'client_uuid': app.client.uuid,
                'url': getattr(app, 'store_url', ''),
                'name': getattr(app, 'name', ''),
            }))
            return

        client = Client.get(self.request.get('client_uuid'))
        if client:
            apps_obj = []
            for app in client.apps:
                apps_obj.append({
                    'uuid': app.uuid,
                    'client_uuid': app.client.uuid,
                    'url': getattr(app, 'store_url', ''),
                    'name': getattr(app, 'name', ''),
                })
            self.response.out.write(json.dumps({
                'apps': apps_obj
            }))
            return

        self.error(404)
        return