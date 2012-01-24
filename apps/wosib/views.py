#!/usr/bin/env python

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc"

import re, urllib

from django.utils               import simplejson as json
from google.appengine.api       import urlfetch
from google.appengine.api       import memcache
from google.appengine.api       import taskqueue 
from google.appengine.ext       import webapp
from google.appengine.ext.webapp      import template
from google.appengine.ext.webapp.util import run_wsgi_app
from time                       import time
from urlparse                   import urlparse

from apps.wosib.actions         import *
from apps.app.models            import *
from apps.client.shopify.models import *
from apps.order.models          import *
from apps.product.shopify.models import ProductShopify
from apps.wosib.models           import WOSIBInstance
from apps.wosib.models           import PartialWOSIBInstance
from apps.wosib.shopify.models   import WOSIBShopify
from apps.stats.models          import Stats

from util.consts                import *
from util.helpers               import *
from util.urihandler            import URIHandler
from util.strip_html import strip_html


class ShowWOSIBButton (webapp.RequestHandler):
    """ """
    
    def get(self):
        url = self.request.get('url')

        # Finally, render the HTML!
        path = os.path.join('apps/wosib/templates/', 'wosib_button.js')
        
        template_values = {
            
        }
        
        self.response.headers.add_header('P3P', P3P_HEADER)
        self.response.out.write(template.render(path, template_values))
        return


class ShowWOSIBInstancePage (URIHandler):
    ''' Unlike the Should I Buy This app, voters do not vote on the same page
        as the asker's cart. This renders a voting page for voters to vote on
        the cart's items, stored in a "WOSIBInstance". '''
    def get (self):
        variants = [] # populate this to show product variants on design page.
        variants = ProductShopify.all().filter('variant =', 0).get()
        template_values = { 'URL'           : URL,
                            'app_uuid'      : self.request.get('app_uuid'),
                            'user_uuid'     : self.request.get('user_uuid'),
                            'instance_uuid' : self.request.get('instance_uuid'),
                            'target_url'    : self.request.get('target_url'),
                            'evnt'          : self.request.get('evnt'),
                            'variants'      : variants
                          }
        
        path = os.path.join('apps/wosib/templates/', 'vote.html')
        self.response.headers.add_header('P3P', P3P_HEADER)
        self.response.out.write(template.render(path, template_values))
        return


class WOSIBAskDynamicLoader(webapp.RequestHandler):
    """When requested serves a plugin that will contain various functionality
       for sharing information about a purchase just made by one of our clients"""
    def get(self):
        template_values = {
        }

        # Finally, render the HTML!
        path = os.path.join('apps/wosib/templates/', 'ask.html')

        self.response.headers.add_header('P3P', P3P_HEADER)
        self.response.out.write(template.render(path, template_values))
        return


class WOSIBPreAskDynamicLoader(webapp.RequestHandler):
    """When requested serves a plugin that will contain various functionality
       for sharing information about a purchase just made by one of our clients"""
    def get(self):
        template_values = {
        }

        # Finally, render the HTML!
        path = os.path.join('apps/wosib/templates/', 'preask.html')

        self.response.headers.add_header('P3P', P3P_HEADER)
        self.response.out.write(template.render(path, template_values))
        return


class WOSIBVoteDynamicLoader(webapp.RequestHandler):
    """When requested serves a plugin that will contain various functionality
       for sharing information about a purchase just made by one of our clients"""
    def get(self):
        template_values = {
        }

        # Finally, render the HTML!
        path = os.path.join('apps/wosib/templates/', 'vote.html')

        self.response.headers.add_header('P3P', P3P_HEADER)
        self.response.out.write(template.render(path, template_values))
        return


class WOSIBShowResults(webapp.RequestHandler):
    """ Shows the results of an instance """
    def get(self):
        template_values = {
        }

        # Finally, render the HTML!
        path = os.path.join('apps/wosib/templates/', 'results.js')

        self.response.headers.add_header('P3P', P3P_HEADER)
        self.response.out.write(template.render(path, template_values))
        return


class WOSIBShowFBThanks( URIHandler ):
    """ Called to show fb_thanks.html. 
        We know the user jsut shared on FB, so create an instance etc. """
    def get(self):
        template_values = {
        }

        # Finally, render the HTML!
        path = os.path.join('apps/wosib/templates/', 'thanks.html')

        self.response.headers.add_header('P3P', P3P_HEADER)
        self.response.out.write(template.render(path, template_values))
        return


class WOSIBColorboxJSServer( URIHandler ):
    def get( self ):
        template_values = { 'URL'           : URL,
                            'app_uuid'      : self.request.get('app_uuid'),
                            'user_uuid'     : self.request.get('user_uuid'),
                            'instance_uuid' : self.request.get('instance_uuid'),
                            'target_url'    : self.request.get('target_url') }
       
        path = os.path.join('apps/wosib/templates/js/', 'jquery.colorbox.js')
        self.response.headers.add_header('P3P', P3P_HEADER)
        self.response.out.write(template.render(path, template_values))
        return

class ShowWOSIBUnloadHook (URIHandler):
    ''' Creates a local-domain iframe that allows SJAX requests to be served
        when the window unloads. (Typically, webkit browsers do not complete 
        onunload functions unless a synchronous AJAX is sent onbeforeunload, and
        in order to send synced requests, the request must be sent to the same
        domain.)'''
    def get (self):
        template_values = { 'URL'           : URL,
                            'app_uuid'      : self.request.get('app_uuid'),
                            'user_uuid'     : self.request.get('user_uuid'),
                            'instance_uuid' : self.request.get('instance_uuid'),
                            'target_url'    : self.request.get('target_url'),
                            'evnt'          : self.request.get('evnt')
                          }
        
        path = os.path.join('apps/wosib/templates/', 'onunloadhook.html')
        self.response.headers.add_header('P3P', P3P_HEADER)
        self.response.out.write(template.render(path, template_values))
        return
