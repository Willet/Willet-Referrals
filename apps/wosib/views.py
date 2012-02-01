
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
# from google.appengine.ext       import db
from time                       import time
from urlparse                   import urlparse

from apps.wosib.actions         import *
from apps.app.models            import *
from apps.client.shopify.models import *
from apps.link.models           import Link
from apps.link.models           import create_link
from apps.link.models           import get_link_by_willt_code
from apps.order.models          import *
from apps.product.models         import Product
from apps.product.shopify.models import ProductShopify # shouldn't be here?
from apps.wosib.models           import WOSIBInstance
from apps.wosib.models           import PartialWOSIBInstance
from apps.wosib.shopify.models   import WOSIBShopify
from apps.stats.models          import Stats
from apps.user.models           import get_user_by_cookie

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


class WOSIBVoteDynamicLoader (URIHandler):
    ''' Unlike the Should I Buy This app, voters do not vote on the same page
        as the asker's cart. This renders a voting page for voters to vote on
        the cart's items, stored in a "WOSIBInstance". '''
    def get (self):
        products = [] # populate this to show product variants on design page.
        try:
            instance_uuid = self.request.get('instance_uuid')
            wosib_instance = WOSIBInstance.get_by_uuid (instance_uuid)
            if not wosib_instance:
                # it could be in memcache still
                wosib_instance = PartialWOSIBInstance.get_by_uuid (instance_uuid)
            instance_product_uuids = [x for x in wosib_instance.products.split(',')] # as # ["id","id","id"]
            # no sane man would compare more than 1000 products from his cart
            products = Product.all().filter('uuid IN', instance_product_uuids).fetch(1000)
            template_values = { 'instance_uuid' : instance_uuid,
                                'products'      : products
                              }
            
            path = os.path.join('apps/wosib/templates/', 'vote.html')
            self.response.headers.add_header('P3P', P3P_HEADER)
            self.response.out.write(template.render(path, template_values))
        except:
            logging.error ('ono', exc_info = True)
        return

class WOSIBAskDynamicLoader(webapp.RequestHandler):
    """When requested serves a plugin that will contain various functionality
       for sharing information about a purchase just made by one of our clients"""
    def get(self):
        try:
            variant_ids = map(lambda x: long(x), self.request.get('variants').split(','))
        except: # if user throws in random crap in the query string, no biggie
            variant_ids = []
        
        if variant_ids: # only if variants are valid, render the page
            logging.debug ("variant_ids = %s" % variant_ids)
            variants = []
            for variant_id in variant_ids:
                its_product = ProductShopify.all().filter ('variants = ', str(variant_id)).get()
                if its_product: # could be None of Product is somehow not in DB
                    variants.append({
                        'id' : its_product.shopify_id,
                        'image' : '/static/imgs/noimage-willet.png', # its_product.images[0],
                        'title' : its_product.title,
                        'variant_id' : variant_id,
                        'product_uuid' : its_product.uuid,
                    })
                else:
                    logging.debug ("Product for variant %s not found in DB" % variant_id)
            
            store_domain  = self.request.get('store_url')
            app           = WOSIBShopify.get_by_store_url(self.request.get('store_url'))
            user          = User.get(self.request.get('user_uuid'))
            user_found    = 1 if hasattr(user, 'fb_access_token') else 0
            user_is_admin = user.is_admin() if isinstance( user , User) else False
            target        = self.request.get( 'target_url' )
            
            refer_url = "%s%s?instance_uuid=%s" % (URL, url('WOSIBVoteDynamicLoader'), self.request.get('instance_uuid'))
            link = Link.create(target, app, refer_url, user)
            
            template_values = {
                'URL' : URL,
                'app_uuid' : self.request.get('app_uuid'),
                'user_uuid' : self.request.get('user_uuid'),
                'instance_uuid' : self.request.get('instance_uuid'),
                'target_url' : self.request.get('target_url'),
                'evnt' : self.request.get('evnt'),
                'FACEBOOK_APP_ID': app.settings['facebook']['app_id'],
                'app': app,
                'willt_url': refer_url, # link.get_willt_url(),
                'willt_code': '',
                'variants' : variants,
                'fb_redirect' : "%s%s" % (URL, url( 'WOSIBShowFBThanks' )),
                'store_domain' : self.request.get( 'store_url' ),
                'title'  : "Which one should I buy?",
                'images' : ['%s/static/imgs/blank.png' % URL], # blank
                'share_url' : refer_url, # link.get_willt_url(),
            }

            # Finally, render the HTML!
            path = os.path.join('apps/wosib/templates/', 'ask.html')

            self.response.headers.add_header('P3P', P3P_HEADER)
            self.response.out.write(template.render(path, template_values))
        return

class WOSIBShowResults(webapp.RequestHandler):
    """ Shows the results of an instance """
    def get(self):
        instance_uuid = self.request.get( 'instance_uuid' )
        wosib_instance = WOSIBInstance.get_by_uuid (instance_uuid)
        instance_products = wosib_instance.products.split(',') # uuid,uuid,uuid
        instance_product_votes = [WOSIBVoteAction.all().filter('instance_uuid =', instance_uuid).filter('product_uuid =', product_uuid).count() for product_uuid in instance_products] # [votes,votes,votes]
        instance_product_dict = dict (zip (instance_products, instance_product_votes)) # {uuid: votes, uuid: votes,uuid: votes}
        
        winning_product_uuid = instance_products[instance_product_votes.index(max(instance_product_votes))]
        
        template_values = {
            'product'  : Product._get_from_datastore (winning_product_uuid),
        }
        
        logging.info("instance_product_dict = %r" % instance_product_dict)
        logging.info("instance_products = %r" % instance_products)
        logging.info("instance_product_votes = %r" % instance_product_votes)

        # Finally, render the HTML!
        path = os.path.join('apps/wosib/templates/', 'results.html')

        self.response.headers.add_header('P3P', P3P_HEADER)
        self.response.out.write(template.render(path, template_values))
        return


class WOSIBShowFBThanks( URIHandler ):

    # http://barbara-willet.appspot.com/s/fb_thanks.html?post_id=122604129_220169211387499#_=_
    def get( self ):
        email       = ""
        user_cancelled = True
        app         = None
        post_id     = self.request.get( 'post_id' ) # from FB
        user        = get_user_by_cookie( self )
        partial     = PartialWOSIBInstance.get_by_user( user )
        
        if post_id != "":
            user_cancelled = False

            # Grab stuff from PartialWOSIBInstance
            app      = partial.app_
            link     = partial.link
            products = partial.products # is "id,id,id", not object!

            # Make the Instance!

            try:
                # given all those products, get one of them, and use its image
                product = Product.get_by_uuid (products.split(',')[0])
                product_image = product.images[0]
            except:
                # either no products, no images in products, or... 
                product_image = '%s/static/imgs/blank.png' % URL # blank
            instance = app.create_instance(user, None, link, products)
            #                              user, end,  link, products
            
            # increment link stuff
            link.app_.increment_shares()
            link.add_user(user)
            logging.info('incremented link and added user')
        
        elif partial != None:
            # Create cancelled action
            WOSIBNoConnectFBCancelled.create( user, 
                                             url=partial.link.target_url,
                                             app=partial.app_ )

        if partial:
            # Now, remove the PartialInstance. We're done with it!
            partial.delete()

        template_values = { 'email'          : user.get_attr( 'email' ),
                            'user_cancelled' : user_cancelled }
        
        path = os.path.join('apps/wosib/templates/', 'fb_thanks.html')
        self.response.headers.add_header('P3P', P3P_HEADER)
        self.response.out.write(template.render(path, template_values))
        return

class ShowWOSIBButtonCSS (URIHandler):
    def get( self ):
        template_values = { 'URL'           : URL,
                            'app_uuid'      : self.request.get('app_uuid')}
       
        path = os.path.join('apps/wosib/templates/css/', 'wosib_user_style.css')
        self.response.headers.add_header('P3P', P3P_HEADER)
        self.response.out.write(template.render(path, template_values))
        return

class ShowWOSIBColorboxCSS (URIHandler):
    def get( self ):
        template_values = { 'URL'           : URL,
                            'app_uuid'      : self.request.get('app_uuid')}
       
        path = os.path.join('apps/wosib/templates/css/', 'colorbox.css')
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
