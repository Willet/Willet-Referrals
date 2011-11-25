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
from google.appengine.ext import db

from apps.app.shopify.models import AppShopify
from apps.sibt.models     import SIBT 
from apps.email.models    import Email
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
    button_css = db.StringProperty(default=None,required=False)
    defaults = {
        '._willet_button': {
            'color': '333333',
            'text-size': '12',
            'border-width': '1',
            'border-color': '777777',
            'background-gradient-start': 'eeeeee',
            'background-gradient-end': 'cccccc',
            'height': '28',
            'border-radius': '0.2',
            'margin-top': '5',
            'margin-right': '0',
            'margin-bottom': '5',
            'margin-left': '0',
            'padding-top': '2',
            'padding-right': '5',
            'padding-bottom': '0',
            'padding-left': '5',
            'font-family': 'Arial, Helvetica',
            'box-shadow-inset': 'rgba(255,255,255,.8)',
            'box-shadow-outset': 'rgba(0,0,0,.3)',
        }, '._willet_button:hover': {
            'background-gradient-start': 'fafafa',
            'background-gradient-end': 'dddddd',
        }, '._willet_button:active': {
            'background-gradient-start': 'fafafa',
            'background-gradient-end': 'fafafa',
        }, '': {
            
        }
    }
    button_default_css = """
        min-width: 202px !important; 
        max-width: 240px !important; 
        height: %(height)spx !important; 
        margin: %(margin-top)spx %(margin-right)spx %(margin-bottom)spx %(margin-left)spx !important; 
        padding: %(padding-top)spx %(padding-right)spx %(padding-bottom)spx %(padding-left)spx !important; 
        clear: both !important; 
        display: none; 
        cursor: pointer !important; 
        font: bold %(text-size)spx/2em %(font-family)s !important; 
        text-decoration: none !important; 
        text-indent: 0px !important; 
        text-align: center !important; 
        text-shadow: 0 1px 0 rgba(255,255,255,.8) !important; 
        line-height: 26px !important; 
        color: #%(color)s !important; 
        background-color: #%(background-gradient-end)s !important; 
        background-image: -webkit-gradient(linear, left top, left bottom, from(#%(background-gradient-start)s), to(#%(background-gradient-end)s)); 
        background-image: -webkit-linear-gradient(top, #%(background-gradient-start)s, #%(background-gradient-end)s); 
        background-image: -moz-linear-gradient(top, #%(background-gradient-start)s, #%(background-gradient-end)s); 
        background-image: -ms-linear-gradient(top, #%(background-gradient-start)s, #%(background-gradient-end)s); 
        background-image: -o-linear-gradient(top, #%(background-gradient-start)s, #%(background-gradient-end)s); 
        background-image: linear-gradient(top, #%(background-gradient-start)s, #%(background-gradient-end)s); 
        filter: progid:DXImageTransform.Microsoft.gradient(startColorStr="#%(background-gradient-start)s", EndColorStr="#%(background-gradient-end)s"); 
        border: %(border-width)spx solid #%(border-color)s !important; 
        -moz-border-radius: %(border-radius)sem; 
        -webkit-border-radius: %(border-radius)sem; 
        border-radius: %(border-radius)sem; 
        box-shadow: 0 0 1px 1px %(box-shadow-inset)s inset, 0 1px 0 %(box-shadow-outset)s; 
        -moz-box-shadow: 0 0 1px 1px %(box-shadow-inset)s inset, 0 1px 0 %(box-shadow-outset)s; 
        -webkit-box-shadow: 0 0 1px 1px %(box-shadow-inset)s inset, 0 1px 0 %(box-shadow-outset)s; 
        vertical-align: baseline; 
        white-space: nowrap !important;"""

    def __init__(self, *args, **kwargs):
        """ Initialize this model """
        super(SIBTShopify, self).__init__(*args, **kwargs)
    
    def do_install(self):
        """Installs this instance"""
        #data = [{
        #    "script_tag": {
        #        "src": "%s/s/shopify/sibt.js?store_id=%s&store_url=%s" % (
        #            URL,
        #            self.store_id,
        #            self.store_url
        #        ),
        #        "event": "onload"
        #    }
        #}]

        script_src = """<!-- START willet sibt for Shopify -->
            <script type="text/javascript">
            (function(window) {
                var hash = window.location.hash;
                var hash_index = hash.indexOf('#code=');
                var willt_code = hash.substring(hash_index + '#code='.length , hash.length);
                var params = "store_url={{ shop.permanent_domain }}&willt_code="+willt_code+"&page_url="+window.location;
                var src = "//%s%s?" + params;
                var script = window.document.createElement("script");
                script.type = "text/javascript";
                script.src = src;
                window.document.getElementsByTagName("head")[0].appendChild(script);
            }(window));
            </script>
            """ % (DOMAIN, reverse_url('SIBTShopifyServeScript'))
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

    def reset_button_css(self):
        self.set_button_css()
        
    def get_button_css_dict(self):
        try:
            assert(self.button_css != None)
            data = json.loads(self.button_css)
            assert(data != None)
        except Exception, e:
            logging.error('could not decode: %s' % self.button_css, exc_info=True)
            data = SIBTShopify.get_default_dict()
        return data

    def set_button_css(self, css=None):
        """Expects a dict"""
        try:
            assert(css != None)
            self.button_css = json.dumps(css)
        except:
            self.button_css = json.dumps(SIBTShopify.get_default_dict()) 
        self.gen_button_css()
        self.put()

    def gen_button_css(self):
        defaults = SIBTShopify.get_default_dict()
        default_css = SIBTShopify.get_default_css()
        logging.error('defaults: %s\ndefault css: %s' % (defaults, default_css))
        try:
            assert(self.button_css != None)
            data = json.loads(self.button_css)
            assert(data != None)
            defaults.update(data)
        except Exception, e:
            logging.error(e, exc_info=True)
            pass
        default_css = default_css % defaults
        default_css = default_css.replace('\n','').replace('\r', '')
        memcache.set('app-%s-button-css' % self.uuid, default_css) 
        return default_css

    def get_button_css(self):
        data = memcache.get('app-%s-button-css' % self.uuid) 
        if data:
            return data
        else:
            return self.gen_button_css()

    @classmethod
    def get_default_dict(cls):
        return cls.button_defaults.copy()

    @classmethod
    def get_default_css(cls):
        return cls.button_default_css

    @classmethod
    def get_default_button_css(cls):
        defaults = cls.get_default_dict()
        button_css = cls.button_default_css % defaults
        button_css = button_css.replace('\n','').replace('\r', '')
        return button_css
        
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

