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
            queues1 = getattr(app, 'queues', [None])  # count of 1
            queues2 = getattr(app, 'queues', [])  # count of 0
            self.respondJSON({
                'uuid': app.uuid,
                'client_uuid': app.client.uuid,
                'url': getattr(app, 'store_url', ''),
                'name': getattr(app, 'name', ''),
                'class': app.__class__.__name__,
                'queue': getattr(queues1[0], 'uuid', ''),
                'queues': [x.uuid for x in queues2]
            }, response_key="app")
            return

        client = Client.get(self.request.get('client_uuid'))
        if client:
            apps_obj = []
            filter_class = self.request.get('class')
            for app in client.apps:
                # generate a list of class names allowed in the filter
                # if one is given, e.g.
                # ['App', 'AppShopify', 'ReEngage', 'ReEngageShopify']
                allowed = [str(x.__name__) for x in app.__class__.__bases__]
                allowed.extend(['App', app.__class__.__name__])

                if app and filter_class and not filter_class in allowed:
                    continue  # this app is not of the requested class.

                queues1 = getattr(app, 'queues', [None])  # count of 1
                queues2 = getattr(app, 'queues', [])  # count of 0
                apps_obj.append({
                    'uuid': app.uuid,
                    'client_uuid': app.client.uuid,
                    'url': getattr(app, 'store_url', ''),
                    'name': getattr(app, 'name', ''),
                    'class': app.__class__.__name__,
                    'queue': getattr(queues1[0], 'uuid', ''),
                    'queues': [x.uuid for x in queues2]
                })
            if len(apps_obj):
                self.respondJSON(apps_obj, response_key="apps")
                return

        self.error(404)
        return