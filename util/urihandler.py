#!/usr/bin/python

__author__ = "Willet Inc."
__copyright__ = "Copyright 2011, Willet Inc."

import logging, os
import inspect

from google.appengine.ext import webapp
from google.appengine.ext.webapp import template

from apps.client.models import Client
from apps.user.models import User
from util.consts import *
from util.cookies import LilCookies
from util.gaesessions import get_current_session
from util.templates import render 


class URIHandler(webapp.RequestHandler):

    def __init__(self):
        # For simple caching purposes. Do not directly access this. Use self.get_client() instead.
        try:
            self.response.headers.add_header('P3P', P3P_HEADER)
        except:
            pass
        self.db_client = None

    # Return None if not authenticated.
    # Otherwise return db instance of client.
    def get_client(self):
        if self.db_client:
            return self.db_client

        session = get_current_session()
        session.regenerate_id()
        email = session.get('email', '')
        if email:
            self.db_client = Client.get_by_email(email)
        else:
            self.db_client = None
        
        #logging.debug ("client by email's db_client = %s -> (%s) %s" % (email, type (self.db_client), self.db_client))

        return self.db_client
    
    def get_browser(self):
        if 'user-agent' in self.request.headers:
                return self.request.headers['user-agent'].lower()
        return '' # default is str(nothing)
    
    def get_user(self):
        """ Reads a cookie, returns user. Does not auto-create. """
        user_cookie = read_user_cookie(self)
        if user_cookie:
            user = User.get(user_cookie)
            if user:
                ip = self.request.remote_addr
                user.add_ip(ip)
                return user

    def render_page(self, template_file_name, content_template_values, template_path=None):
        """This re-renders the full page with the specified template."""
        client = self.get_client()

        template_values = {
            'login_url'  : '/client/login',
            'logout_url' : '/client/logout',
            'URL'        : URL,
            'NAME'       : NAME,
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

        logging.info("Rendering %s" % path)
        self.response.headers.add_header('P3P', P3P_HEADER)
        return render(path, merged_values)
        #return template.render(path, merged_values)

    def get_app_path(self):
        module = inspect.getmodule(self).__name__
        parts = module.split('.')
        app_path = None 

        if len(parts) > 2:
            if parts[0] == 'apps':
                # we have an app
                app_path = '/'.join(parts[:-1])

        return app_path

    def set_cookie(field, value):
        """Sets a cookie on the browser"""
        cookie = LilCookies(self, COOKIE_SECRET)
        cookie.set_secure_cookie(
            name=field,
            value=value,
            expires_days=365*10,
            domain='.%s' % APP_DOMAIN
        )
        
    def get_cookie(field):
        """Retrieves a cookie value from the browser; None if N/A."""
        cookie = LilCookies(self, COOKIE_SECRET)
        return cookie.get_secure_cookie(name=field)

# end class
