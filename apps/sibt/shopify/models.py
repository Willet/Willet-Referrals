#!/usr/bin/python

# SIBTShopify model
# Extends from "Referral", which extends from "App"

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc"

import datetime
import hashlib
import inspect
import logging

from django.utils                   import simplejson as json
from google.appengine.api           import memcache
from google.appengine.datastore     import entity_pb
from google.appengine.ext           import db
from google.appengine.ext.webapp    import template

from apps.app.shopify.models import AppShopify
from apps.client.models      import Client
from apps.email.models       import Email
from apps.sibt.models        import SIBT 
from apps.user.models        import get_user_by_cookie
from util                    import httplib2
from util.consts             import *
from util.helpers            import generate_uuid
from util.helpers            import url as reverse_url

# ------------------------------------------------------------------------------
# SIBTShopify Class Definition -------------------------------------------------
# ------------------------------------------------------------------------------
class SIBTShopify(SIBT, AppShopify):
    # CSS to style the button.
    button_css = db.TextProperty(default=None,required=False)

    # Version number of the app
    # Version 1 = [Beginning, Nov. 22, 2011]
    # Version 2 = [Nov. 23, 2011, Present]
    # Differences between versions: version 1 uses script_tags API to install scripts
    # version 2 uses asset api to include liquid
    # version 3: "sweet buttons upgrade"
    version    = db.StringProperty(default='2', indexed=False)
    
    # STRING property of any integer
    # change on upgrade; new installs get this as version.
    CURRENT_INSTALL_VERSION = '3'
    
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
        }, 'willet_button_v3': {
            'background': '#fff',
            'border': '1px solid #BBB',
            'border_radius': '3', # soften the blow
            'color': '#383f41', # font colour within the box
            'font': '14px Helvetica, Arial, sans-serif',
            'margin': '12px 0',
            'padding': '0 15px',
            'width': '223',
            'height': '88',
            'others': '', # place whatever extra CSS in here
             # text on top of the button
            'p_text_align': 'left',
            'p_margin': '12px 0 0 0',
            'p_padding': '0 !important', # some shopify themes change this
            'p_font_size': '14px !important', # some shopify themes change this
            'p_line_height': '20',
            'p_others': '', # place whatever extra CSS in here
             # button within the frame
            'button_width': '219',
            'button_height': '25',
            'button_margin': '8px auto',
            'button_padding': '4px 2px',
            'button_background_color': '#C1F0F5',
            'button_text_align': 'center',
            'button_border_radius': '4',
            'button_background_image': '''  background-image: linear-gradient(top, #c9f7fa, #a1eff5);
                                            background-image: -o-linear-gradient(top, #c9f7fa, #a1eff5);
                                            background-image: -moz-linear-gradient(top, #c9f7fa, #a1eff5);
                                            background-image: -webkit-linear-gradient(top, #c9f7fa, #a1eff5);
                                            background-image: -ms-linear-gradient(top, #c9f7fa, #a1eff5);
                                       ''',
            'button_box_shadow': '0 1px 0 #BBB',
            'button_shadow_hover': '#BBB',
            'button_others': '', # place whatever extra CSS in here
            'button_hover_others': '', # place whatever extra CSS in here
            'button_img_others': '', # place whatever extra CSS in here
            'button_title_others': '', # place whatever extra CSS in here
        }
    }

    def __init__(self, *args, **kwargs):
        """ Initialize this model """
        super(SIBTShopify, self).__init__(*args, **kwargs)
    
    def do_install(self, email_client=True):
        """Installs this instance"""
        if self.version == '3': # sweet buttons has different on-page snippet.
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
                    data-image_url="{{ product.images[0] | product_img_url: "large" | replace: '?', '%3F' | replace: '&','%26'}}"
                    style="width: 278px;height: 88px;">
                
                </div>
                <!-- END Willet SIBT for Shopify -->"""
        else:
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
        self.install_webhooks( product_hooks_too = True )
        self.install_assets(assets=liquid_assets)

        # Email DevTeam
        Email.emailDevTeam(
            'SIBT Install: %s %s %s' % (
                self.uuid, 
                self.client.name, 
                self.store_url 
            )
        )

        # Fire off "personal" email from Fraser
        if email_client:
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
        success1 = memcache.set(
                self.store_url,
                db.model_to_protobuf(self).Encode(), time=MEMCACHE_TIMEOUT)
        if hasattr (self, 'extra_url'):
            # if you have an extra URL, you need to memcache the app by extra URL as well.
            success2 = memcache.set(
                    self.extra_url,
                    db.model_to_protobuf(self).Encode(), time=MEMCACHE_TIMEOUT)
            return success1 and success2
        return success1

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
            logging.warning (e, exc_info=True)
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
    def create(client, token, email_client=True):
        uuid = generate_uuid( 16 )
        logging.debug("creating SIBTShopify version '%s'" % SIBTShopify.CURRENT_INSTALL_VERSION)
        app = SIBTShopify(
                        key_name = uuid,
                        uuid = uuid,
                        client = client,
                        store_name = client.name, # Store name
                        store_url = client.url, # Store url
                        store_id = client.id, # Store id
                        store_token = token,
                        version = SIBTShopify.CURRENT_INSTALL_VERSION )
        app.put()
        
        app.do_install(email_client)
       
        return app

    @staticmethod
    def get_or_create(client, token=None, email_client=True):
        logging.debug ("in get_or_create, client.url = %s" % client.url)
        app = SIBTShopify.get_by_store_url(client.url)
        if app is None:
            logging.debug ("app not found; creating one.")
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
                    logging.debug ("app.old_client was %s" % app.old_client)
                    app.client      = app.old_client if app.old_client else client
                    app.old_client  = None
                    logging.debug("changing SIBTShopify version to '%s'" % SIBTShopify.CURRENT_INSTALL_VERSION)
                    app.version = SIBTShopify.CURRENT_INSTALL_VERSION # reinstall? update version
                    app.put()

                    app.do_install(email_client)
                except:
                    logging.error('encountered error with reinstall', exc_info=True)
        else:
            # if token is None, i.e. getting, not creating
            pass
        
        logging.debug ("SIBTShopify::get_or_create.app is now %s" % app)
        return app

    @staticmethod
    def get_by_uuid(uuid):
        return SIBTShopify.get(uuid)

    @staticmethod
    def get_by_store_url(url):
        data = memcache.get(url)
        if data:
            return db.model_from_protobuf(entity_pb.EntityProto(data))

        app = SIBTShopify.all().filter('store_url =', url).get()
        if not app:
            # no app in DB by store_url; try again with extra_url
            app = SIBTShopify.all().filter('extra_url =', url).get()
        
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

