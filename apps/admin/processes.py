#!/usr/bin/env python

__author__ = "Willet, Inc."
__copyright__ = "Copyright 2011, Willet, Inc"

import re, logging, urllib

from django.utils import simplejson as json
from google.appengine.api import urlfetch, memcache, mail, taskqueue
from google.appengine.ext.db import ReferencePropertyResolveError
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

from apps.buttons.shopify.models import ButtonsShopify
from apps.link.models import Link

from util.consts import *
from util.helpers import *
from util.mailchimp import MailChimp
from util.urihandler import URIHandler


class UpdateStore(URIHandler):
    def get(self):
        store_url = self.request.get('store')

        app = SIBTShopify.get_by_store_url(store_url)

        if app:
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
            
            app.install_assets(assets=liquid_assets)

            url = '%s/admin/script_tags.json' % app.store_url
            username = app.settings['api_key'] 
            password = hashlib.md5(app.settings['api_secret'] + app.store_token).hexdigest()
            header = {'content-type':'application/json'}
            h = httplib2.Http()
            
            # Auth the http lib
            h.add_credentials(username, password)

            # First fetch webhooks that already exist
            resp, content = h.request(url, "GET", headers = header)
            logging.info('Fetching script_tags: %s' % content)
            data = json.loads(content) 

            for w in data['script_tags']:
                if '%s/s/shopify/sibt.js' % URL in w['src']:
                    url = '%s/admin/script_tags/%s.json' % (app.store_url, w['id'])
                    resp, content = h.request(url, "DELETE", headers = header)
                    logging.info("Uninstalling: URL: %s Result: %s %s" % (url, resp, content))


class EmailBatch(URIHandler):
    """ Emails batch of App clients from offset to batch_size

    Adds another EmailBatch to taskqueue if it reaches limit
    """
    def get (self):
        self.post() # yup, taskqueues are randomly GET or POST.

    def post(self):
        """ Expected inputs:
            - batch_size: (int) 0 - 1000
            - offset: (int) database offset
            - app_cls: App class
            - target_version: (Optional)
            - title: (str) email title
            - body: (str) email body
        """
        batch_size = self.request.get('batch_size')
        offset = self.request.get('offset')
        app_cls = self.request.get('app_cls')
        target_version = self.request.get('target_version')

        if not batch_size or not (offset >= 0) or not app_cls:
            self.error(400) # Bad Request
            return

        apps = db.Query(App).filter('class = ', app_cls).fetch(limit=batch_size, offset=offset)

        # If reached batch size, start another batch at the next offset
        if len(apps) == batch_size:
            params = {
                'batch_size':       batch_size,
                'offset':           offset + batch,
                'app_cls':          app_cls,
                'target_version':   target_version,
                'title':            title,
                'body':             body
            }
            taskqueue.add(url=url('EmailBatch'), params=params)

        # For each app, try to create an email & send it
        for app in all_apps:
            try:
                # Check version
                if target_version >= 0 and app.version != target_version:
                    # Wrong version, skip this one
                    continue

                # Get client name
                if not hasattr (app, 'client'):      # lagging cache
                    raise AttributeError ('Client is missing, likely an uninstall')
                if not hasattr (app.client, 'email'): # bad install
                    raise AttributeError ('Email is missing from client object!')
                if not hasattr (app.client, 'merchant'): # crazy bad install
                    raise AttributeError ('User is missing from client object!')
                    full_name = "shop owner"
                else:
                    full_name = app.client.merchant.full_name
                
                # Create body text
                raw_body_text = self.request.get('body', '')
                raw_body_text = raw_body_text.replace('{{ name }}', full_name.split(' ')[0]).replace('{{name}}', full_name.split(' ')[0])
                
                # Construct email body
                body = template.render(Email.template_path('general_mail.html'),
                    {
                        'title'        : self.request.get('subject'),
                        'content'      : raw_body_text
                    }
                )
                # Remove HTML formatting from email subject line
                subject = re.compile(r'<.*?>').sub('', self.request.get('subject'))
                
                # Construct email
                email = {
                    'client': app.client,
                    'to': 'brian@getwillet.com, fraser@getwillet.com', # you are CC'd
                    #'to': app.client.email,
                    'subject': subject,
                    'body': body
                }

                # Send off email
                taskqueue.add(url=url('EmailSomeone'), params= email)

                logging.info('Sending email to %r' % app.client)

            except Exception, e:
                logging.warn("Error finding client/email for app: %r; %s" % (app, e), exc_info = True)
                pass # miss a client!


class EmailSomeone (URIHandler):
    def get (self):
        self.post() # yup, taskqueues are randomly GET or POST.

    def post(self):
        try:
            Email.send_email (
                self.request.get('from', 'fraser@getwillet.com'),
                self.request.get('to'),
                self.request.get('subject'),
                self.request.get('body'),
                self.request.get('to_name', None),
                self.request.get('reply-to', None)
            )
            self.response.out.write ("200 OK")
        except Exception, e:
            logging.warn("Error sending one of the emails in batch! %s\n%r" % 
                (e, [
                    self.request.get('from', 'fraser@getwillet.com'),
                    self.request.get('to'),
                    self.request.get('subject'),
                    self.request.get('body'),
                    self.request.get('to_name', None),
                    self.request.get('reply-to', None)
                ]), exc_info = True
            )


class UploadEmailsToMailChimp(URIHandler):
    """ One-time use to upload existing ShopConnection customers to MailChimp 
    Remove after use

    MailChimp Docs: http://apidocs.mailchimp.com/api/rtfm/listbatchsubscribe.func.php
    """
    def get(self):
        self.post()

    def post(self):
        batch_size = 50
        offset = int(self.request.get('offset', 0))
        logging.info('Adding ButtonShopify %i-%i to MailChimp' % (offset, offset+batch_size-1))
        batch = []
        name = ''

        apps = db.Query(ButtonsShopify).fetch(offset=offset, limit=batch_size)

        for app in apps:
            if app.client:
                try:
                    name = app.client.merchant.get_full_name()
                except ReferencePropertyResolveError:
                    name = app.client.name
                try:
                    first_name, last_name = name.split(' ')[0], (' ').join(name.split(' ')[1:])
                except AttributeError:
                    # name = None, skip this entry
                    continue
                except IndexError:
                    # Split didn't result in 2 parts
                    first_name, last_name = name, ''
                
                batch.append({ 'FNAME': first_name,
                               'LNAME': last_name,
                               'EMAIL': app.client.email,
                               'STORENAME': app.client.name,
                               'STOREURL': app.client.url })
                logging.info('Adding %s (%s) to MailChimp' % (app.client.name, app.client.url))

        resp = {}
        if 'mailchimp_list_id' in SHOPIFY_APPS['ButtonsShopify']:
            email_list_id = SHOPIFY_APPS['ButtonsShopify']['mailchimp_list_id']

            if email_list_id:
                try:
                    resp = MailChimp(MAILCHIMP_API_KEY).listBatchSubscribe(id=email_list_id,
                                                                       batch=batch,
                                                                       double_optin=False,
                                                                       update_existing=True,
                                                                       send_welcome=False)
                    # Response can be:
                    #     <bool> True / False (unsubscribe worked, didn't work)
                    #     <dict> error + message
                except Exception, e:
                    # This is bad form to except everything, but we really can't have a failure on install
                    logging.error('ListBatchSubscribe to ShopConnection FAILED: %r' % (e,), exc_info=True)
                else:
                    try:
                        if 'error' in resp:
                            logging.warning('ListBatchSubscribe to ShopConnection FAILED: %r' % (resp,))
                    except TypeError:
                        # thrown when results is not iterable (eg bool)
                        logging.info('ListBatchSubscribed to ShopConnection OK: %r' % (resp,))
                    else:
                        logging.info('ListBatchSubscribe to ShopConnection OK: %r' % (resp,))                        

        # Keep going if haven't reached end
        if len(apps) == batch_size:
            logging.info('Add next batch: %i-%i' % (offset+batch_size, offset+2*batch_size-1))
            taskqueue.add(url=url('UploadEmailsToMailChimp'), params={'offset': offset+batch_size})
        return


class SIBTReset (URIHandler):
    # TODO: make BatchRequest
    def get(self):
        sibt_apps = App.all().filter('class =', 'SIBTShopify').fetch(500)

        # Update apps, and get async db puts rolling
        for sibt_app in sibt_apps:
            sibt_app.button_enabled = True
            sibt_app.top_bar_enabled = False
            db.put_async(sibt_app)

        # Now update memcache
        for sibt_app in sibt_apps:
            key = sibt_app.get_key()
            if key:
                memcache.set(key, db.model_to_protobuf(sibt_app).Encode(), time=MEMCACHE_TIMEOUT)

        self.response.out.write("Done")


class GenerateOlderHourPeriods(URIHandler):
    def get(self):
        if self.request.get('reset'):
            memcache.delete_multi(['day', 'hour', 'day_global', 'hour_global'])
        else:
            ensure = self.request.get('ensure')

            oldest_global = GlobalAnalyticsHourSlice.all().order('start').get()
            hour_global = oldest_global.start - datetime.timedelta(hours=1)
            memcache.set('hour_global', hour_global)

            global_day = GlobalAnalyticsDaySlice.all().order('start').get()
            day_global = global_day.start - datetime.timedelta(days=1)
            memcache.set('day_global', day_global.date())

            oldest_app = AppAnalyticsHourSlice.all().order('start').get() 
            hour = oldest_app.start - datetime.timedelta(hours=1)
            memcache.set('hour', hour)

            oldest_day = AppAnalyticsDaySlice.all().order('start').get()
            day = oldest_day.start - datetime.timedelta(days=1)
            memcache.set('day', day.date())

            if ensure in ['day', 'hour', 'day_global', 'hour_global']:
                urlfetch.fetch('%s/bea/ensure/%s/' % (URL, ensure))

        self.response.out.write(json.dumps({'success':True}))


class AnalyticsRPC(URIHandler):
    @admin_required
    def get(self, admin):
        limit = self.request.get('limit') or 3
        offset = self.request.get('offset') or 0
        
        day_slices = GlobalAnalyticsDaySlice.all()\
                .order('-start')\
                .fetch(int(limit), offset=int(offset))
        data = []
        for ds in day_slices:
            obj = {}

            obj['start'] = str(ds.start)
            obj['start_day'] = str(ds.start.date())
            
            for action in actions_to_count:
                obj[action] = ds.get_attr(action)
            data.append(obj)

        response = {
            'success': True,
            'data': data 
        }

        self.response.out.write(json.dumps(response))


class AppAnalyticsRPC(URIHandler):
    def get(self, app_uuid):
        app = App.get(app_uuid)
        limit = self.request.get('limit') or 3
        offset = self.request.get('offset') or 0
        
        day_slices = AppAnalyticsDaySlice.all()\
                .filter('app_ =', app)\
                .order('-start')\
                .fetch(int(limit), offset=int(offset))
        data = []
        for ds in day_slices:
            obj = {}

            obj['start'] = str(ds.start)
            obj['start_day'] = str(ds.start.date())
            
            for action in actions_to_count:
                obj[action] = ds.get_attr(action)
            data.append(obj)

        response = {
            'success': True,
            'data': data 
        }

        self.response.out.write(json.dumps(response))


class TrackRemoteError(URIHandler):
    def get(self):
        referer = self.request.headers.get('referer')
        ua = self.request.headers.get('user-agent')
        remote_ip = self.request.remote_addr
        error = self.request.get('error')
        script = self.request.get('script')
        stack_trace = self.request.get('st')
        mail.send_mail(
            sender = 'rf.rs error reporting <Barbara@rf.rs>',
            to = 'fraser@getwillet.com',
            subject = 'Javascript callback error',
            body = """We encountered an error
                Page:       %s
                Script:     %s
                User Agent: %s
                Remote IP:  %s
                Error Name: %s
                Error Message:
                %s""" % (
                    referer,
                    script,
                    ua,
                    remote_ip,
                    error,
                    stack_trace
            )
        )
        self.redirect('%s/static/imgs/noimage.png' % URL)

