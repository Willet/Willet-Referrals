#!/usr/bin/env python

__author__ = "Willet, Inc."
__copyright__ = "Copyright 2012, Willet, Inc"

import logging
import urllib2

from google.appengine.ext.webapp import template
from random import choice
from urlparse import urlparse, urlunsplit

from apps.app.models import *
from apps.client.shopify.models import *
from apps.link.models import Link
from apps.order.models import *
from apps.product.models import Product
from apps.user.models import User
from apps.wosib.actions import *
from apps.wosib.models import PartialWOSIBInstance, WOSIBInstance
from apps.wosib.shopify.models import WOSIBShopify

from util.consts import *
from util.helpers import *
from util.strip_html import strip_html
from util.urihandler import URIHandler


class WOSIBVoteDynamicLoader (URIHandler):
    """ Unlike the Should I Buy This app, voters do not vote on the same page
        as the asker's cart. This renders a voting page for voters to vote on
        the cart's items, stored in a "WOSIBInstance". """
    def get (self):
        products = [] # populate this to show products on design page.
        share_url = ''
        try:
            instance_uuid = self.request.get('instance_uuid')
            wosib_instance = WOSIBInstance.get(instance_uuid)
            # no sane man would compare more than 1000 products from his cart
            products = Product.all().filter('uuid IN', wosib_instance.products).fetch(1000)
            logging.info ("products = %r" % products)
            
            try:
                share_url = wosib_instance.link.get_willt_url()
            except AttributeError, e:
                logging.warn ('Faulty link')
                
            
            template_values = { 'instance_uuid' : instance_uuid,
                                'products'      : products,
                                'share_url'     : share_url
                              }
            
            path = os.path.join('apps/wosib/templates/', 'vote.html')
            self.response.headers.add_header('P3P', P3P_HEADER)
            self.response.out.write(template.render(path, template_values))
        except:
            logging.error ('ono', exc_info = True)
        return


class WOSIBAskDynamicLoader(URIHandler):
    """When requested serves a plugin that will contain various functionality
       for sharing information about a purchase just made by one of our clients"""
    def get(self):
        ids = []
        link = None
        products = []
        template_products = []
        uuids = []
        user = None

        store_domain = self.request.get('store_url')
        refer_url = self.request.get('refer_url')
        logging.info ("refer_url = %s" % refer_url)

        # get_or_create a WOSIB app.
        app = WOSIBShopify.get_by_store_url(store_domain)
        if not app:
            app = WOSIB.get_by_store_url(store_domain)
        if not app:
            sibt = SIBTShopify.get_by_store_url(store_domain)
            if sibt:
                app = WOSIBShopify.get_or_create(sibt.client,
                                                 token=sibt.store_token,
                                                 email_client=False)
            if not sibt:
                sibt = SIBT.get_by_store_url(store_domain)
                if sibt:  # if site contains 
                    app = WOSIB.get_or_create(sibt.client,
                                              domain=sibt.client.domain)
        if not app:
            msg = "app not found."
            logging.warning(msg)
            self.response.out.write(msg)
            return

        user = User.get(self.request.get('user_uuid'))
        user_found = 1 if hasattr(user, 'fb_access_token') else 0
        user_is_admin = user.is_admin() if isinstance(user , User) else False

        # if both are present and extra_url needs to be filled...
        if store_domain and refer_url and not hasattr(app, 'extra_url'):
            """Checks if refer_url (almost always window.location.href)
            has the same domain as store url

            Example: http://social-referral.appspot.com/w/ask.html?
                     store_url=http://thegoodhousewife.myshopify.com
                    &refer_url=http://thegoodhousewife.co.nz/cart&...
            """
            try:
                url_parts = urlparse(refer_url)

                # is "abc.myshopify.com" part of the store URL, "http://abc.myshopify.com"?
                if url_parts.netloc not in urllib2.unquote(store_domain):
                    # save the alternative URL so it can be called back later.
                    app.extra_url = "%s://%s" % (url_parts.scheme, url_parts.netloc)
                    logging.info("[WOSIB] associating a new URL, %s, with the original, %s" % (app.extra_url, app.store_url))
                    app.put()
            except:
                pass  # can't decode target as URL; oh well!

        # get product UUIDs from the query string
        try:
            uuids = [str(x) for x in self.request.get('products').split(',')]
            products = [Product.get(uuid) for uuid in uuids]
        except NameError, ValueError:
            # if user throws in random crap in the query string, no biggie
            pass

        if not uuids:  # get product (shopify) IDs from the query string
            try:  # convert IDs back to UUIDs
                ids = [str(x) for x in self.request.get('ids').split(',')]
                products = Product.all()\
                                  .filter ('shopify_id IN ', ids)\
                                  .fetch(limit=10)
                uuids = [p.uuid for p in products]
            except NameError, ValueError:
                pass

        # uuids is empty: do nothing
        if not products:
            msg = "Incorrect calling method - products not found."
            logging.warning(msg)
            self.response.out.write(msg)
            return

        # one product: Render SIBT b/c only 1 product
        if len(products) == 1:
            logging.debug ('Only one product - switched to SIBT!')
            self.redirect("%s?%s&products=%s" % (url('AskDynamicLoader'),
                                                 self.request.query_string,
                                                 uuids[0]))
            return

        # more than one product: WOSIB
        for product in products:
            if product: # could be None of Product is somehow not in DB
                if len(product.images) > 0:
                    image = product.images[0] # can't catch LIOOR w/try
                else:
                    image = '/static/imgs/noimage-willet.png'

                template_products.append({
                    'id': product.shopify_id,
                    'uuid': product.uuid,
                    'image': image,
                    'title': product.title,
                    'shopify_id': product.shopify_id,
                    'product_uuid': product.uuid,
                    'product_desc': product.description,
                })
            else:
                logging.warning("Product of UUID %s not found in DB" % uuid)

        if not template_products:
            """do not raise ValueError - "UnboundLocalError:
            local variable 'ValueError' referenced before assignment"
            """
            raise Exception('UUIDs did not correspond to products')

        target = "%s%s?instance_uuid=%s" % (URL,
                                            url('WOSIBVoteDynamicLoader'),
                                            self.request.get('instance_uuid'))

        link = Link.create(target, app, refer_url, user)

        try:
            # pick random product, use it for showing description
            random_product = choice(template_products)
            random_image = random_product['image']
        except IndexError: # if our chosen product happens to have no image
            logging.error('No products found! Using plain image.')
            random_image = ['%s/static/imgs/blank.png' % URL] # blank

        template_values = {
            'URL' : URL,
            'app_uuid': self.request.get('app_uuid'),
            'user_uuid': self.request.get('user_uuid'),
            'instance_uuid': self.request.get('instance_uuid'),
            'target_url': self.request.get('refer_url'),
            'evnt': self.request.get('evnt'),
            'FACEBOOK_APP_ID': app.settings['facebook']['app_id'],
            'app': app,
            'willt_code': link.willt_url_code, # used to create full instances
            'products': template_products,
            'fb_redirect': "%s%s" % (URL, url('WOSIBShowFBThanks')),
            'store_domain': self.request.get('store_url'),
            'title' : "Which one should I buy?",
            'product_desc': random_product['product_desc'],
            'image': random_image,
            'share_url': link.get_willt_url(), # refer_url
        }

        # Finally, render the HTML!
        path = os.path.join('apps/wosib/templates/', 'ask.html')

        self.response.headers.add_header('P3P', P3P_HEADER)
        self.response.out.write(template.render(path, template_values))
        return

class WOSIBShowResults(URIHandler):
    """ Shows the results of an instance """
    def get(self):
        instance_uuid = self.request.get('instance_uuid')
        wosib_instance = WOSIBInstance.get(instance_uuid)
        if not wosib_instance:
            raise Exception ('instance not found')
            
        winning_products = wosib_instance.get_winning_products()
        if len(winning_products) > 1:
            # that is, if multiple items have the same score
            template_values = {
                'products': winning_products,
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
                'product': winning_products[0],
                'product_image': product_image,
                'has_product_link': bool(product_link),
                'product_link': product_link
            }
            # Finally, render the HTML!
            path = os.path.join('apps/wosib/templates/', 'results.html')

        self.response.headers.add_header('P3P', P3P_HEADER)
        self.response.out.write(template.render(path, template_values))
        return


class WOSIBShowFBThanks(URIHandler):

    # http://barbara-willet.appspot.com/s/fb_thanks.html?post_id=122604129_220169211387499#_=_
    def get(self):
        email = ""
        user_cancelled = True
        app = None
        post_id = self.request.get('post_id') # from FB
        user = User.get_by_cookie(self)
        partial = PartialWOSIBInstance.get_by_user(user)
        
        if post_id != "":
            user_cancelled = False

            # Grab stuff from PartialWOSIBInstance
            app = partial.app_
            link = partial.link 
            products = partial.products # is ["id","id","id"], not object!

            # Make the Instance!

            try:
                # given all those products, get one of them, and use its image
                product = Product.get(products[0])
                product_image = product.images[0]
            except:
                # either no products, no images in products, or... 
                product_image = '%s/static/imgs/blank.png' % URL # blank
            instance = app.create_instance(user, None, link, products)
            #                              user, end,  link, products
            
            # partial's link is actually bogus (points to vote.html without an instance_uuid)
            # this adds the full WOSIB instance_uuid to the URL, so that the vote page can
            # be served.
            link.target_url = urlunsplit([PROTOCOL,
                                          DOMAIN,
                                          url('WOSIBVoteDynamicLoader'),
                                          ('instance_uuid=%s' % instance.uuid),
                                          ''])
            logging.info ("link.target_url changed to %s (%s)" % (link.target_url, instance.uuid))
            # increment link stuff
            link.app_.increment_shares()
            link.add_user(user)
            link.put()
            link.memcache_by_code() # doubly memcached
            
            logging.info('incremented link and added user')
        
        elif partial != None:
            # Create cancelled action
            #WOSIBNoConnectFBCancelled.create(user, 
            #                                  url=partial.link.target_url,
            #                                  app=partial.app_)
            pass # TODO: WOSIB Analytics

        if partial:
            # Now, remove the PartialInstance. We're done with it!
            partial.delete()

        template_values = {
            'email': user.get_attr('email'),
            'user_cancelled': user_cancelled
        }
        
        path = os.path.join('apps/wosib/templates/', 'fb_thanks.html')
        self.response.headers.add_header('P3P', P3P_HEADER)
        self.response.out.write(template.render(path, template_values))
        return


class ShowWOSIBColorboxCSS (URIHandler):
    def get(self):
        template_values = {
            'URL': URL,
            'app_uuid': self.request.get('app_uuid')
        }
       
        path = os.path.join('apps/plugin/templates/css/', 'colorbox.css')
        self.response.headers.add_header('P3P', P3P_HEADER)
        self.response.out.write(template.render(path, template_values))
        return


class WOSIBColorboxJSServer(URIHandler):
    def get(self):
        template_values = {
            'URL': URL,
            'app_uuid': self.request.get('app_uuid'),
            'user_uuid': self.request.get('user_uuid'),
            'instance_uuid': self.request.get('instance_uuid'),
            'refer_url': self.request.get('refer_url')
        }
       
        path = os.path.join('apps/wosib/templates/js/', 'jquery.colorbox.js')
        self.response.headers['Content-Type'] = 'application/javascript'
        self.response.headers.add_header('P3P', P3P_HEADER)
        self.response.out.write(template.render(path, template_values))
        return
