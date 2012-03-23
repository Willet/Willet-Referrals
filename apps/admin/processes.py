#!/usr/bin/env python

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc"

import re, urllib

from django.utils import simplejson as json
from google.appengine.api import urlfetch, memcache
from google.appengine.ext import webapp
from google.appengine.api import mail, taskqueue
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

from apps.link.models import Link

from util.consts import *
from util.helpers import *
from util.urihandler import URIHandler


class UpdateStore( URIHandler ):
    def get(self):
        store_url = self.request.get( 'store' )

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

            url      = '%s/admin/script_tags.json' % app.store_url
            username = app.settings['api_key'] 
            password = hashlib.md5(app.settings['api_secret'] + app.store_token).hexdigest()
            header   = {'content-type':'application/json'}
            h        = httplib2.Http()
            
            # Auth the http lib
            h.add_credentials(username, password)

            # First fetch webhooks that already exist
            resp, content = h.request( url, "GET", headers = header)
            logging.info( 'Fetching script_tags: %s' % content )
            data = json.loads( content ) 

            for w in data['script_tags']:
                if '%s/s/shopify/sibt.js' % URL in w['src']:
                    url = '%s/admin/script_tags/%s.json' % (app.store_url, w['id'] )
                    resp, content = h.request( url, "DELETE", headers = header)
                    logging.info("Uninstalling: URL: %s Result: %s %s" % (url, resp, content) )


class EmailBatch(URIHandler):
    """ Emails batch of App clients from offset to batch_size

    Adds another EmailBatch to taskqueue if it reaches limit
    """
    def get (self):
        self.post() # yup, taskqueues are randomly GET or POST.

    def post( self ):
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
    """
    def get(self):
        pass

    def post(self):
        # http://apidocs.mailchimp.com/api/rtfm/listbatchsubscribe.func.php
        apps = db.Query(App).filter('class = ', 'ButtonsShopify').fetch()

        for app in apps:
            if app.client:
                batch.append({ 'FNAME': first_name,
                               'LNAME': last_name,
                               'STORENAME': self.client.name,
                               'STOREURL': self.client.url })

        MailChimp(MAILCHIMP_API_KEY).listBatchSubscribe(id='98231a9737', # ShopConnection list
                                                        email_address=self.client.email,
                                                        batch=batch,
                                                        double_optin=False,
                                                        update_existing=True,
                                                        send_welcome=False)
        self.response.out.write('Done')
        # pass


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


class TrackRemoteError(webapp.RequestHandler):
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

