#!/usr/bin/python

# SIBTShopify model
# Extends from "Referral", which extends from "App"

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc"

import hashlib
import logging
import datetime
import inspect

from django.utils         import simplejson as json
from google.appengine.ext import db
from google.appengine.api import memcache
from google.appengine.datastore import entity_pb
from google.appengine.ext.webapp import template

from apps.app.shopify.models import AppShopify
from apps.sibt.models     import SIBT 
from apps.email.models    import Email
from apps.user.models import get_user_by_cookie
from util                 import httplib2
from util.consts          import *
from util.helpers         import generate_uuid
from util.helpers import url as reverse_url

# ------------------------------------------------------------------------------
# SIBTShopify Class Definition -------------------------------------------------
# ------------------------------------------------------------------------------
class SIBTShopify(SIBT, AppShopify):
    
    # Shopify's ID for this store
    #store_id    = db.StringProperty( indexed = True )

    # Shopify's token for this store
    #store_token = db.StringProperty( indexed = True )
    button_css = db.TextProperty(default=None,required=False)
    defaults = {
        'willet_button': {
            'color': '333333',
            'text_size': '12',
            'width': '240',
            'border_width': '1',
            'border_color': '777777',
            'line_height': '26',
            'background_gradient_start': 'eeeeee',
            'background_gradient_end': 'cccccc',
            'height': '28',
            'border_radius': '0.2',
            'margin_top': '5',
            'margin_right': '0',
            'margin_bottom': '5',
            'margin_left': '0',
            'padding_top': '2',
            'padding_right': '5',
            'padding_bottom': '0',
            'padding_left': '5',
            'font_family': 'Arial, Helvetica',
            'box_shadow_inset': 'rgba(255,255,255,.8)',
            'box_shadow_outset': 'rgba(0,0,0,.3)',
        }, 'willet_button__hover': {
            'color': '333333',
            'border_color': '777777',
            'border_width': '1',
            'background_gradient_start': 'fafafa',
            'background_gradient_end': 'dddddd',
        }, 'willet_button__active': {
            'color': '333333',
            'border_color': '777777',
            'border_width': '1',
            'background_gradient_start': 'fafafa',
            'background_gradient_end': 'fafafa',
        }, 'willet_sibt_top_bar': {
            'background_color': '3B5998',
        }, 'willet_bottom_tab': {
            'color': '0000000',
            'background_color': 'FFFF00',
            'font_size': '14',
            'font_family': 'Arial, Helvetica',
            'box_shadow_color': '727272',
            'border_radius': '10',
            'padding': '10'
                
        } 

    }

    def __init__(self, *args, **kwargs):
        """ Initialize this model """
        super(SIBTShopify, self).__init__(*args, **kwargs)
    
    def do_install(self):
        """Installs this instance"""
        script_src = """<!-- START willet sibt for Shopify -->
            <script type="text/javascript">
            (function(window) {
                var hash = window.location.hash;
                var hash_index = hash.indexOf('#code=');
                var willt_code = hash.substring(hash_index + '#code='.length , hash.length);
                var params = "store_url={{ shop.permanent_domain }}&willt_code="+willt_code+"&page_url="+window.location;
                var src = "http://%s%s?" + params;
                var script = window.document.createElement("script");
                script.type = "text/javascript";
                script.src = src;
                window.document.getElementsByTagName("head")[0].appendChild(script);
            }(window));
            </script>""" % (DOMAIN, reverse_url('SIBTShopifyServeScript'))
        willet_snippet = script_src + """
            <div id="_willet_shouldIBuyThisButton" data-merchant_name="{{ shop.name | escape }}"
                data-product_id="{{ product.id }}" data-title="{{ product.title | escape  }}"
                data-price="{{ product.price | money }}" data-page_source="product"
                data-image_url="{{ product.images[0] | product_img_url: "large" | replace: '?', '%3F' | replace: '&','%26'}}"></div>
            <!-- END Willet SIBT for Shopify -->"""

        liquid_assets = [{
            'asset': {
                'value': willet_snippet,
                'key': 'snippets/willet_sibt.liquid'
            }
        }]
        # Install yourself in the Shopify store
        self.install_webhooks()
        #self.install_script_tags(script_tags=data)
        self.install_assets(assets=liquid_assets)

        # Email Barbara
        Email.emailBarbara(
            'SIBT Install: %s %s %s' % (
                self.uuid, 
                self.client.name, 
                self.store_url 
            )
        )

        # Fire off "personal" email from Fraser
        Email.welcomeClient( "Should I Buy This", 
                             self.client.merchant.get_attr('email'), 
                             self.client.merchant.get_full_name(), 
                             self.client.name )

    def put(self):
        """So we memcache by the store_url as well"""
        logging.info('enhanced SIBTShopify put')
        super(SIBTShopify, self).put()
        self.memcache_by_store_url()

    def memcache_by_store_url(self):
        return memcache.set(
                self.store_url, 
                db.model_to_protobuf(self).Encode(), time=MEMCACHE_TIMEOUT)

    def reset_css(self):
        self.set_css()
        
    def get_css_dict(self):
        try:
            assert(self.button_css != None)
            data = json.loads(self.button_css)
            assert(data != None)
        except Exception, e:
            #logging.error('could not decode: %s\n%s' % 
            #        (e, self.button_css), exc_info=True)
            data = SIBTShopify.get_default_dict()
        return data

    def set_css(self, css=None):
        """Expects a dict"""
        try:
            assert(css != None)
            self.button_css = json.dumps(css)
        except:
            #logging.info('setting to default')
            self.button_css = json.dumps(SIBTShopify.get_default_dict()) 
        self.generate_css()
        self.put()

    def generate_css(self):
        class_defaults = SIBTShopify.get_default_dict()
        logging.info('class_defaults : %s' % class_defaults )
        try:
            assert(self.button_css != None)
            data = json.loads(self.button_css)
            assert(data != None)
            #logging.warn('updating with data:\n%s' % data)
            class_defaults.update(data)
        except Exception, e:
            #logging.error(e, exc_info=True)
            pass
        css = SIBTShopify.generate_default_css(class_defaults)
        memcache.set('app-%s-sibt-css' % self.uuid, css) 
        return css 

    def get_css(self):
        data = memcache.get('app-%s-sibt-css' % self.uuid) 
        if data:
            return data
        else:
            return self.generate_css()

    @classmethod
    def get_default_dict(cls):
        return cls.defaults.copy()

    @classmethod
    def get_default_css(cls):
        return cls.generate_default_css() 

    @classmethod
    def generate_default_css(cls, values=None):
        """Uses the values dict to generate the sibt css"""
        if not values:
            values = cls.get_default_dict()
        path = 'apps/sibt/templates/css/sibt_user_style.css'
        rendered = template.render(path, values)
        rendered = rendered.replace('\n', '').replace('\r','')
        return rendered

    @classmethod
    def get_default_button_css(cls):
        logging.warn('this method shouldnt be used: get_default_button_css')
        return cls.get_default_css()
        
    @staticmethod
    def create(client, token):
        uuid = generate_uuid( 16 )
        app = SIBTShopify(
                        key_name    = uuid,
                        uuid        = uuid,
                        client      = client,
                        store_name  = client.name, # Store name
                        store_url   = client.url, # Store url
                        store_id    = client.id, # Store id
                        store_token = token)
        app.put()
        
        app.do_install()
        
        return app

    @staticmethod
    def get_or_create(client, token=None):
        app = SIBTShopify.get_by_store_url(client.url)
        if app is None:
            app = SIBTShopify.create(client, token)
        elif token != None and token != '':
            if app.store_token != token:
                # TOKEN mis match, this might be a re-install
                logging.warn(
                    'We are going to reinstall this app because the stored token \
                    does not match the request token\n%s vs %s' % (
                        app.store_token,
                        token
                    )
                ) 
                try:
                    app.store_token = token
                    app.client      = app.old_client
                    app.old_client  = None
                    app.put()

                    app.do_install()
                except:
                    logging.error('encountered error with reinstall', exc_info=True)
        return app

    @staticmethod
    def get_by_uuid(uuid):
        return SIBTShopify.get(uuid)

    @staticmethod
    def get_by_store_url(url):
        data = memcache.get(url)
        if data:
            app = db.model_from_protobuf(entity_pb.EntityProto(data))
        else:
            app = SIBTShopify.all()\
                .filter('store_url =', url)\
                .get()
            if app:
                app.memcache_by_store_url()

        return app

    @staticmethod
    def get_by_store_id(store_id):
        logging.info("Shopify: Looking for %s" % store_id)
        logging.warn('THIS METHOD IS DEPRECATED: %s' % inspect.stack()[0][3])
        return SIBTShopify.all()\
                .filter('store_id =', store_id)\
                .get()

# Constructor ------------------------------------------------------------------
def create_sibt_shopify_app(client, token):
    logging.warn('THIS METHOD IS DEPRECATED: %s' % inspect.stack()[0][3])
    uuid = generate_uuid( 16 )
    app = SIBTShopify( key_name    = uuid,
                       uuid        = uuid,
                       client      = client,
                       store_name  = client.name, # Store name
                       store_url   = client.url, # Store url
                       store_id    = client.id, # Store id
                       store_token = token )
    app.put()
    
    app.do_install()
     
    return app

# Accessors --------------------------------------------------------------------
def get_or_create_sibt_shopify_app(client, token=None):
    logging.warn('THIS METHOD IS DEPRECATED: %s' % inspect.stack()[0][3])
    #app = get_sibt_shopify_app_by_store_id( client.id )
    app = get_sibt_shopify_app_by_store_url(client.url)
    if app is None:
        app = create_sibt_shopify_app(client, token)
    elif token != None and token != '':
        if app.store_token != token:
            # TOKEN mis match, this might be a re-install
            logging.warn(
                'We are going to reinstall this app because the stored token \
                does not match the request token\n%s vs %s' % (
                    app.store_token,
                    token
                )
            ) 
            try:
                app.store_token = token
                app.put()
                app.do_install()
            except:
                logging.error('encountered error with reinstall', exc_info=True)
    return app

def get_sibt_shopify_app_by_uuid(id):
    """ Fetch a Shopify obj from the DB via the uuid"""
    logging.info("Shopify: Looking for %s" % id)
    logging.warn('THIS METHOD IS DEPRECATED: %s' % inspect.stack()[0][3])
    return SIBTShopify.get(id)
    #return SIBTShopify.all()\
    #        .filter('uuid =', id)\
    #        .get()

def get_sibt_shopify_app_by_store_url(url):
    """ Fetch a Shopify obj from the DB via the store's url"""
    logging.info("Shopify: Looking for %s" % url)
    logging.warn('THIS METHOD IS DEPRECATED: %s' % inspect.stack()[0][3])
    return SIBTShopify.all()\
            .filter('store_url =', url)\
            .get()

def get_sibt_shopify_app_by_store_id(id):
    """ Fetch a Shopify obj from the DB via the store's id"""
    logging.info("Shopify: Looking for %s" % id)
    logging.warn('THIS METHOD IS DEPRECATED: %s' % inspect.stack()[0][3])
    return SIBTShopify.all()\
            .filter('store_id =', id)\
            .get()

