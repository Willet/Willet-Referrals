#!/usr/bin/python

"""The SIBTShopify model.

Extends from SIBT/App.
"""

__author__ = "Willet, Inc."
__copyright__ = "Copyright 2012, Willet, Inc"

import inspect
import logging
from datetime import datetime

from django.utils import simplejson as json
from google.appengine.api import memcache
from google.appengine.ext import db
from google.appengine.ext.webapp import template

from apps.app.shopify.models import AppShopify
from apps.email.models import Email
from apps.sibt.models import SIBT
from util.consts import DOMAIN
from util.helpers import generate_uuid
from util.helpers import url as reverse_url


class SIBTShopify(SIBT, AppShopify):
    # CSS to style the button (deprecated for SIBTShopify v10+)
    button_css = db.TextProperty(default=None, required=False)

    def _validate_self(self):
        return True

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
            'border': 'none',
            'border_radius': '3', # soften the blow
            'color': '#383f41', # font colour within the box
            'font': '14px Helvetica, Arial, sans-serif',
            'margin': '0',
            'padding': '0',
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
            'button_background_image': """  background-image: linear-gradient(top, #c9f7fa, #a1eff5);
                                            background-image: -o-linear-gradient(top, #c9f7fa, #a1eff5);
                                            background-image: -moz-linear-gradient(top, #c9f7fa, #a1eff5);
                                            background-image: -webkit-linear-gradient(top, #c9f7fa, #a1eff5);
                                            background-image: -ms-linear-gradient(top, #c9f7fa, #a1eff5);
                                       """,
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

    # Retreivers --------------------------------------------------------------
    @classmethod
    def get_by_uuid(cls, uuid):
        return cls.get(uuid)

    @classmethod
    def get_by_store_id(cls, store_id):
        return cls.all().filter('store_id =', store_id).get()

    # Constructors ------------------------------------------------------------
    @staticmethod
    def create(client, token, email_client=True):
        uuid = generate_uuid(16)
        logging.debug("Creating SIBTShopify version '%s'" % SIBTShopify.CURRENT_INSTALL_VERSION)
        app = SIBTShopify(
            key_name=uuid,
            uuid=uuid,
            client=client,
            store_name=client.name, # Store name
            store_url=client.url, # Store url
            store_id=client.id, # Store id
            store_token=token,
            version=SIBTShopify.CURRENT_INSTALL_VERSION
        )
        app.put()

        app.do_install(email_client)

        return app

    # 'Retreive or Construct'ers ----------------------------------------------
    @classmethod
    def get_or_create(cls, client, token=None, email_client=True):
        # logging.debug ("in get_or_create, client.url = %s" % client.url)
        app = cls.get_by_store_url(client.url)
        if app is None:
            app = cls.create(client, token)
        elif token != None and token != '':
            if app.store_token != token:
                # TOKEN mis match, this might be a re-install
                logging.warn("Reinstalling app.")
                try:
                    app.store_token = token
                    app.client = app.old_client if app.old_client else client
                    app.old_client = None
                    app.version = cls.CURRENT_INSTALL_VERSION # reinstall? update version
                    app.created = datetime.utcnow()
                    app.put()

                    app.do_install(email_client)
                except:
                    logging.error('Encountered error with reinstall:', exc_info=True)
        else:
            # if token is None, i.e. getting, not creating
            pass
        return app

    # Shopify API calls -------------------------------------------------------
    def do_install(self, email_client=True):
        """Installs this app."""

        # SIBT2 (cart page snippet)
        wosib_script_src = """<!-- START Willet (http://rf.rs) Cart snippet -->
            <div id="_willet_WOSIB_Button" style="width:278px;height:88px;"></div>
            <script type="text/javascript">
                var _willet_wosib_script = "//%s%s?store_url={{ shop.permanent_domain }}";
                var _willet_cart_items = [
                    {%% for item in cart.items %%}
                        { "image" : "{{ item.image }}", // url
                          "title" : "{{ item.title }}", // or "name"
                          "id" : "{{ item.product.id }}",
                          "product_url" : "{{ item.product.url }}"
                        }{%% unless forloop.last %%},{%% endunless %%}
                    {%% endfor %%}
                ];

                (function (s) {
                    s.type = "text/javascript";
                    s.src = _willet_wosib_script;
                    document.getElementsByTagName("head")[0].appendChild(s);
                }(document.createElement("script")));
            </script>""" % (DOMAIN, reverse_url('SIBTServeScript'))

        # SIBT2 (multiple products)
        if self.version == '10':
            willet_snippet = """
                <!-- START Willet (http://rf.rs) Product page snippet -->
                <div id="_willet_shouldIBuyThisButton" data-merchant_name="{{ shop.name | escape }}"
                    data-product_id="{{ product.id }}" data-title="{{ product.title | escape  }}"
                    data-price="{{ product.price | money }}" data-page_source="product"
                    data-image_url="{{ product.images[0] | product_img_url: "large" | replace: '?', '%%3F' | replace: '&','%%26'}}">
                </div>
                <script type="text/javascript">
                (function(w, d) {
                    var hash = w.location.hash;
                    var willt_code = hash.substring(hash.indexOf('#code=') + '#code='.length , hash.length);
                    var product_json = {{ product | json }};
                    var params = "store_url={{ shop.permanent_domain }}&willt_code="+willt_code+"&page_url="+w.location;
                    if (product_json) {
                        w._willet_product_json = product_json;
                        params += '&product_id=' + product_json.id;
                    }
                    var src = "//%s%s?" + params;
                    var script = d.createElement("script");
                    script.type = "text/javascript";
                    script.src = src;
                    d.getElementsByTagName("head")[0].appendChild(script);
                }(window, document));
                </script>
                <!-- END Willet SIBT for Shopify -->""" % (DOMAIN, reverse_url('SIBTShopifyServeScript'))
        elif self.version == '3': # sweet buttons has different on-page snippet.
            script_src = """<!-- START willet (http://rf.rs) sibt for Shopify -->
                <script type="text/javascript">
                (function(window) {
                    var hash = window.location.hash;
                    var willt_code = hash.substring(hash.indexOf('#code=') + '#code='.length , hash.length);
                    var product_json = {{ product | json }};
                    var params = "store_url={{ shop.permanent_domain }}&willt_code="+willt_code+"&page_url="+window.location;
                    if (product_json) {
                        params += '&product_id=' + product_json.id;
                    }
                    var src = "//%s%s?" + params;
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
            script_src = """<!-- START willet (http://rf.rs) sibt for Shopify -->
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
        },{
            'asset': {
                'value': wosib_script_src,
                'key': 'snippets/willet_wosib.liquid'
            }
        }]
        # Install yourself in the Shopify store
        self.queue_webhooks(product_hooks_too=True)
        self.queue_assets(assets=liquid_assets)

        self.install_queued()

        # Email DevTeam
        Email.emailDevTeam(
            'SIBT Install: %s %s %s' % (
                self.uuid,
                self.client.name,
                self.store_url
            ),
            subject='SIBT installed'
        )

        # Fire off "personal" email from Fraser
        if email_client:
            Email.welcomeClient("Should I Buy This",
                                 self.client.merchant.get_attr('email'),
                                 self.client.merchant.get_full_name(),
                                 self.client.name)

    # CSS Methods -------------------------------------------------------------
    def reset_css(self):
        self.set_css()

    def get_css_dict(self):
        try:
            if not self.button_css:
                raise Exception("No CSS")
            data = json.loads(self.button_css)
            if not data:
                raise Exception("No data")
        except Exception, e:
            #logging.error('could not decode: %s\n%s' %
            #        (e, self.button_css), exc_info=True)
            data = SIBTShopify.get_default_dict()
        return data

    def set_css(self, css=None):
        """Expects a dict"""
        try:
            if not css:
                raise Exception("No CSS")
            self.button_css = json.dumps(css)
        except:
            #logging.info('setting to default')
            self.button_css = json.dumps(SIBTShopify.get_default_dict())
        self.generate_css()
        self.put()

    def generate_css(self):
        class_defaults = SIBTShopify.get_default_dict()
        logging.info('class_defaults : %s' % class_defaults)
        try:
            if not self.button_css:
                raise Exception("No CSS")
            data = json.loads(self.button_css)
            if not data:
                raise Exception("No data")
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
        logging.error('Deprecated method get_default_button_css should be\
                       replaced by %s.get_default_css: %s' % (cls,  inspect.stack()[0][3]))
        return cls.get_default_css()