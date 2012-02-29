#!/usr/bin/env python

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2012, Willet, Inc"

import re, urllib

from django.utils                     import simplejson as json
from google.appengine.api             import urlfetch
from google.appengine.api             import memcache
from google.appengine.api             import taskqueue 
from google.appengine.ext             import webapp
from google.appengine.ext.webapp      import template
from google.appengine.ext.webapp.util import run_wsgi_app
from random                           import choice
from time                             import time
from urlparse                         import urlparse

from apps.app.models                  import *
from apps.client.shopify.models       import *
from apps.link.models                 import Link
from apps.order.models                import *
from apps.product.models              import Product
from apps.user.models                 import get_user_by_cookie
from apps.wosib.actions               import *
from apps.wosib.models                import WOSIBInstance
from apps.wosib.models                import PartialWOSIBInstance
from apps.wosib.shopify.models        import WOSIBShopify

from util.consts                      import *
from util.helpers                     import *
from util.strip_html                  import strip_html
from util.urihandler                  import URIHandler


class WOSIBVoteDynamicLoader (URIHandler):
    ''' Unlike the Should I Buy This app, voters do not vote on the same page
        as the asker's cart. This renders a voting page for voters to vote on
        the cart's items, stored in a "WOSIBInstance". '''
    def get (self):
        products = [] # populate this to show product variants on design page.
        try:
            instance_uuid = self.request.get('instance_uuid')
            wosib_instance = WOSIBInstance.get_by_uuid (instance_uuid)
            # no sane man would compare more than 1000 products from his cart
            products = Product.all().filter('uuid IN', wosib_instance.products).fetch(1000)
            logging.info ("products = %r" % products)
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
                variant_product = Product.all().filter ('variants = ', str(variant_id)).get()
                if variant_product: # could be None of Product is somehow not in DB
                    if len(variant_product.images) > 0:
                        image = variant_product.images[0] # can't catch LIOOR w/try
                    else:
                        image = '/static/imgs/noimage-willet.png'
                    variants.append({
                        'id' : variant_product.shopify_id,
                        'image' : image,
                        'title' : variant_product.title,
                        'variant_id' : variant_id,
                        'product_uuid' : variant_product.uuid,
                        'product_desc' : variant_product.description,
                    })
                else:
                    logging.debug ("Product for variant %s not found in DB" % variant_id)
            
            store_domain  = self.request.get('store_url')
            refer_url = self.request.get( 'refer_url' )
            logging.info ("refer_url = %s" % refer_url)
            app = WOSIBShopify.get_by_store_url(store_domain)

            # if both are present and extra_url needs to be filled...
            if store_domain and refer_url and not hasattr(app, 'extra_url'):
                ''' check if refer_url (almost always window.location.href) has the same domain as store url
                    example: http://social-referral.appspot.com/w/ask.html?
                         store_url=http://thegoodhousewife.myshopify.com
                        &refer_url=http://thegoodhousewife.co.nz/cart
                        &variants=109751342
                        &app_uuid=9d9fd05f5db0497b
                        &user_uuid=1e1cdedac5914319
                        &instance_uuid=
                '''
                try:
                    url_parts = urlparse (refer_url)
                    if url_parts.netloc not in urllib2.unquote(store_domain): # is "abc.myshopify.com" part of the store URL, "http://abc.myshopify.com"?
                        app.extra_url = "%s://%s" % (url_parts.scheme, url_parts.netloc) # save the alternative URL so it can be called back later.
                        logging.info ("[WOSIB] associating a new URL, %s, with the original, %s" % (app.extra_url, app.store_url))
                        app.put()
                except:
                    pass # can't decode target as URL; oh well!
            
            user          = User.get(self.request.get('user_uuid'))
            user_found    = 1 if hasattr(user, 'fb_access_token') else 0
            user_is_admin = user.is_admin() if isinstance( user , User) else False
            target        = "%s%s?instance_uuid=%s" % (URL, url('WOSIBVoteDynamicLoader'), self.request.get('instance_uuid'))
            
            link = Link.create (target, app, refer_url, user)
            
            random_variant = choice(variants) # pick random variant, use it for showing description
            try:
                random_image = random_variant.images[0]
            except: # if our chosen variant happens to have no image
                random_image = ['%s/static/imgs/blank.png' % URL], # blank
            
            template_values = {
                'URL' : URL,
                'app_uuid' : self.request.get('app_uuid'),
                'user_uuid' : self.request.get('user_uuid'),
                'instance_uuid' : self.request.get('instance_uuid'),
                'target_url' : self.request.get('refer_url'),
                'evnt' : self.request.get('evnt'),
                'FACEBOOK_APP_ID': app.settings['facebook']['app_id'],
                'app': app,
                'willt_code': link.willt_url_code, # used to create full instances
                'variants' : variants,
                'fb_redirect' : "%s%s" % (URL, url( 'WOSIBShowFBThanks' )),
                'store_domain' : self.request.get( 'store_url' ),
                'title'  : "Which one should I buy?",
                'product_desc' : random_variant['product_desc'],
                'images' : random_image,
                'share_url' : link.get_willt_url(), # refer_url
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
        if not wosib_instance:
            raise Exception ('instance not found')
            
        winning_products = wosib_instance.get_winning_products()
        if len(winning_products) > 1:
            # that is, if multiple items have the same score
            template_values = {
                'products'  : winning_products,
            }
            # Finally, render the HTML!
            path = os.path.join('apps/wosib/templates/', 'results-multi.html')
        else:
            # that is, if one product is winning the voting
            try:
                product_image = winning_products[0].images[0]
            except:
                product_image = '/static/imgs/noimage-willet.png' # no image default
            
            try:
                product_link = winning_products[0].link
            except:
                product_link = '' # no image default

            template_values = {
                'product'  : winning_products[0],
                'product_image' : product_image,
                'has_product_link' : bool (product_link),
                'product_link': product_link
            }
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
            products = partial.products # is ["id","id","id"], not object!

            # Make the Instance!

            try:
                # given all those products, get one of them, and use its image
                product = Product.get_by_uuid (products[0])
                product_image = product.images[0]
            except:
                # either no products, no images in products, or... 
                product_image = '%s/static/imgs/blank.png' % URL # blank
            instance = app.create_instance(user, None, link, products)
            #                              user, end,  link, products
            
            # partial's link is actually bogus (points to vote.html without an instance_uuid)
            # this adds the full WOSIB instance_uuid to the URL, so that the vote page can
            # be served.
            link.target_url = "%s://%s%s?instance_uuid=%s" % (PROTOCOL, DOMAIN, url ('WOSIBVoteDynamicLoader'), instance.uuid)
            logging.info ("link.target_url changed to %s (%s)" % (link.target_url, instance.uuid))
            # increment link stuff
            link.app_.increment_shares()
            link.add_user(user)
            link.put()
            link.memcache_by_code() # doubly memcached
            
            logging.info('incremented link and added user')
        
        elif partial != None:
            # Create cancelled action
            #WOSIBNoConnectFBCancelled.create( user, 
            #                                  url=partial.link.target_url,
            #                                  app=partial.app_ )
            pass # TODO: WOSIB Analytics

        if partial:
            # Now, remove the PartialInstance. We're done with it!
            partial.delete()

        template_values = { 'email'          : user.get_attr( 'email' ),
                            'user_cancelled' : user_cancelled }
        
        path = os.path.join('apps/wosib/templates/', 'fb_thanks.html')
        self.response.headers.add_header('P3P', P3P_HEADER)
        self.response.out.write(template.render(path, template_values))
        return

class ShowWOSIBColorboxCSS (URIHandler):
    def get( self ):
        template_values = { 'URL'           : URL,
                            'app_uuid'      : self.request.get('app_uuid')}
       
        path = os.path.join('apps/plugin/templates/css/', 'colorbox.css')
        self.response.headers.add_header('P3P', P3P_HEADER)
        self.response.out.write(template.render(path, template_values))
        return

class WOSIBColorboxJSServer( URIHandler ):
    def get( self ):
        template_values = { 'URL'           : URL,
                            'app_uuid'      : self.request.get('app_uuid'),
                            'user_uuid'     : self.request.get('user_uuid'),
                            'instance_uuid' : self.request.get('instance_uuid'),
                            'refer_url'     : self.request.get('refer_url') }
       
        path = os.path.join('apps/wosib/templates/js/', 'jquery.colorbox.js')
        self.response.headers['Content-Type'] = 'application/javascript'
        self.response.headers.add_header('P3P', P3P_HEADER)
        self.response.out.write(template.render(path, template_values))
        return
