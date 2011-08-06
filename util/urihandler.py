#!/usr/bin/python

__author__      = "Willet Inc."
__copyright__   = "Copyright 2011, Willet Inc."

import os

from gaesessions                 import get_current_session
from google.appengine.ext        import webapp
from google.appengine.ext.webapp import template

from models.client   import get_client_by_email
from util.consts     import *

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
    
    def render_page(self, template_file_name, content_template_values):
        """This re-renders the full page with the specified template."""
        client = self.get_client()

        template_values = {
            'login_url'  : '/login',
            'logout_url' : '/logout',
            'URL'        : URL,
            'NAME'       : NAME,
            'client'     : client
        }
        merged_values = dict(template_values)
        merged_values.update(content_template_values)

        path = os.path.join('templates/' + template_file_name )
        return template.render(path, merged_values)
