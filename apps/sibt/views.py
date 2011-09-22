#!/usr/bin/env python

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc"

import re, urllib

from django.utils import simplejson as json
from google.appengine.api import urlfetch, memcache
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app
from time import time
from urlparse import urlparse

from apps.action.models       import SIBTClickAction, get_sibt_click_actions_by_user_for_url
from apps.app.models          import *
from apps.sibt.models         import get_sibt_instance_by_asker_for_url
from apps.sibt.shopify.models import SIBTShopify, get_sibt_shopify_app_by_store_id
from apps.link.models         import Link, get_link_by_willt_code, create_link
from apps.user.models         import get_user_by_cookie, User, get_or_create_user_by_cookie
from apps.client.models       import *
from apps.order.models        import *
from apps.stats.models        import Stats

from util.helpers             import *
from util.urihandler          import URIHandler
from util.consts              import *



class DynamicLoader(webapp.RequestHandler):
    """When requested serves a plugin that will contain various functionality
       for sharing information about a purchase just made by one of our clients"""
    
    def get(self):
        template_values = {}
            
        origin_domain = os.environ['HTTP_REFERER'] if\
            os.environ.has_key('HTTP_REFERER') else 'UNKNOWN'
        
        page_url = urlparse( self.request.remote_addr )
        target   = "%s://%s%s" % (page_url.scheme, page_url.netloc, page_url.path)
        if target == "://127.0.0.1":
            target = 'http://www.rf.rs' # HACK
            origin_domain = 'http://www.rf.rs' # HACK

        # Grab a User and App
        user = get_or_create_user_by_cookie(self)
        app  = get_sibt_shopify_app_by_store_id( self.request.get('store_id') )
       
        # Make a new Link
        link = create_link( target, app, origin_domain, user )

        template_values = {
                'product_img' : self.request.get( 'photo' ),
                'FACEBOOK_APP_ID' : FACEBOOK_APP_ID,
                'app' : app,
                'willt_url' : link.get_willt_url() if link else '',
                
                'user': user,
        }

        # Finally, render the HTML!
        path = os.path.join('apps/sibt/templates/', 'ask.html')
        self.response.out.write(template.render(path, template_values))
        return
