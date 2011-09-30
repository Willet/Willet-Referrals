#!/usr/bin/env python

import os
import logging
from django.utils import simplejson as json

from google.appengine.ext import webapp
from google.appengine.ext.webapp import template

from apps.buttons.shopify.models import * 
from apps.app.models import App
#from apps.user.models import get_or_create_user_by_cookie
from apps.client.models import ClientShopify
from apps.link.models import create_link, get_link_by_url

from util.consts import *
from util.helpers import get_request_variables
from util.urihandler import URIHandler

class ButtonsShopifyBeta(URIHandler):
    def get(self):
        template_values = {
            "SHOPIFY_API_KEY": SHOPIFY_APPS['ButtonsShopify']['api_key']
        }
        
        self.response.out.write(self.render_page('beta.html', template_values))

class ButtonsShopifyEditAjax(URIHandler):
    def post(self, button_id):
        # handle posting from the edit form
        client = self.get_client()
        
        response = {}

        button = ButtonsShopify.all().filter('uuid =', button_id).get()
        if button == None:
            response['status'] = False
        else:
            response['status'] = True

        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(json.dumps(response))

class ButtonsShopifyEdit(URIHandler):
    def get(self, button_id):
        # show the edit form
        client = self.get_client()

        button = ButtonsShopify.all().filter('uuid =', button_id).get()
        if button == None:
            self.redirect('/b/shopify/')

        template_values = {
            'button': button,        
            'client': client
        }

        self.response.out.write(self.render_page('edit.html', template_values))

class ButtonsShopifyWelcome(URIHandler):
    def get( self ):
        client = self.get_client() # May be None
       
        # TODO: put this somewhere smarter
        app_token = self.request.get( 't' )
        app = get_or_create_buttons_shopify_app(client, app_token)
        
        shop_owner = 'a Shopify store'
        if client:
            shop_owner = client.merchant.get_attr('full_name')

        template_values = {
            'app'        : app,
            'shop_owner' : shop_owner 
        }

        self.response.out.write(self.render_page('welcome.html', template_values)) 

class ButtonsShopifyList(URIHandler):
    def get(self):
        # show the buttons enabled for this site
        client = self.get_client()
        if client:
            shop_owner = client.merchant.get_attr('full_name')
        else:
            shop_owner = 'Awesomer Bob'

        template_values = {
            'query_string': self.request.query_string,
            'shop_owner': shop_owner 
        }
        
        self.response.out.write(self.render_page('list.html', template_values))

class ButtonsShopifyJS(webapp.RequestHandler):
    """When requested serves a plugin that will contain various functionality
       for sharing information about a purchase just made by one of our clients"""
    def get(self, input_path):
        template_values = {}
        rq_vars = get_request_variables(['store_url', 'demo'], self)

        if os.environ.has_key('HTTP_REFERER'):
            origin_domain = os.environ['HTTP_REFERER'] 
        else:
            origin_domain = 'UNKNOWN'

        is_demo = (rq_vars['demo'] != '')
        
        # set the stylesheet we are going to use
        style = self.request.get('style')
        if style == '':
            style = 'shopify'

        app = None
        client = None

        # try getting the app if we can
        app_id = self.request.get('app_id')
        if app_id != None:
            app = App.all().filter('uuid =', app_id).get()
            #get the client too!
            if app != None:
                client = app.client 
        else:
            # cant get the app, so get the client first
            app = None
        
        if client == None:
            client = ClientShopify.all().filter('url =', rq_vars['store_url']).get()
        
        # If they give a bogus app id, show the landing page app!
        if app == None:
            app = ButtonsShopify.all().filter('client =', client).get()

        # Make a new Link
        link = get_link_by_url(origin_domain)
        if link == None:
            # link does not exist yet
            # we create links with no user
            link = create_link(self.request.url, app, origin_domain, None)

        template_values = {
            'app' : app,
            'app_uuid' : app.uuid,
            'willt_url' : link.get_willt_url(),
            'willt_code': link.willt_url_code,
            'want_text': 'I want this!',
            'URL': URL, 
            'FACEBOOK_APP_ID': BUTTONS_FACEBOOK_APP_ID,
        }
    
        if self.request.url.startswith('http://localhost'):
            template_values['BASE_URL'] = self.request.url[0:21]
        else:
            template_values['BASE_URL'] = URL
        
        # Finally, render the plugin!
        path = os.path.join('apps/buttons/templates/', input_path)
        
        if input_path.find('.js') != -1:
            self.response.headers['Content-Type'] = 'javascript'
        else:
            self.response.headers['Content-Type'] = 'text/html'
        self.response.out.write(template.render(path, template_values))
        return

