#!/usr/bin/python

__author__      = "Willet Inc."
__copyright__   = "Copyright 2011, Willet Inc."

import logging, os
import inspect

from google.appengine.ext        import webapp
from google.appengine.ext.webapp import template

from apps.client.models import get_client_by_email
from util.consts     import *
from util.gaesessions import get_current_session

class URIHandler( webapp.RequestHandler ):

    def __init__(self):
        # For simple caching purposes. Do not directly access this. Use self.get_client() instead.
        self.db_client = None

    # Return None if not authenticated.
    # Otherwise return db instance of client.
    def get_client(self):
        if self.db_client:
            return self.db_client

        session = get_current_session()
        session.regenerate_id()
        email   = session.get('email', '');
        
        self.db_client = get_client_by_email( email )
            
        if not self.db_client:
            pass

        return self.db_client
    
    def render_page(self, template_file_name, content_template_values, template_path=None):
        """This re-renders the full page with the specified template."""
        client = self.get_client()

        template_values = {
            'login_url'  : '/client/login',
            'logout_url' : '/client/logout',
            'URL'        : URL,
            'NAME'       : NAME,
            'MIXPANEL_TOKEN' : MIXPANEL_TOKEN,
            'client'     : client
        }
        merged_values = dict(template_values)
        merged_values.update(content_template_values)
        
        path = os.path.join('templates/', template_file_name)
        
        app_path = self.get_app_path()
        
        if template_path != None:
            logging.info('got template_path: %s' % template_path)
            path = os.path.join(template_path, path)
        elif app_path != None:
            path = os.path.join(app_path, path)

        logging.info("Rendering %s" % path )
        return template.render(path, merged_values)

    def get_app_path(self):
        module = inspect.getmodule(self).__name__
        parts = module.split('.')
        app_path = None 

        if len(parts) > 2:
            if parts[0] == 'apps':
                # we have an app
                app_path = '/'.join(parts[:-1])

        return app_path

