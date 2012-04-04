#!/usr/bin/python

# The AppShopify Model
# A parent class for all Shopify social 'apps'

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc"

import base64
import hashlib
import datetime
import re

from django.utils           import simplejson as json
from google.appengine.api   import urlfetch
from google.appengine.ext   import db
from google.appengine.runtime import DeadlineExceededError

from apps.app.models        import App
from apps.email.models      import Email

from util                   import httplib2
from util.consts            import *
from util.errors           import ShopifyAPIError, ShopifyBillingError
from util.shopify_helpers   import *
from util.model             import Model

NUM_SHARE_SHARDS = 15

class AppShopify(Model):
    """ Model for storing information about a Shopify App.
        AppShopify classes need not be installable from the Shopify app store,
        and can be installed as a bundle. Refer to SIBTShopify for example code.

        How Shopify Charges Work:

            Two options, one-time charge or recurring billing

            Both work with same workflow:

            a) Customer requests charging page
            b) We make Shopify API call, specifying return_url (on our domain)
            c) Shopify responds with confirmation_url
            d) We redirect customer to confirmation_url (on shopify domain)
            e) Customer decides & is sent to return_url?charge_id=### with confirmed / denied status
            *f) We make Shopify API call to activate the charge
            g) Shopify responds with 200 OK

            *We actually hit the Shopify API 1st to get all of the charge info
            before requesting activation.  There is a lot of junk we don't want to
            store that needs to be included in the activation request

            Note: only 1 recurring billing plan can exist for each store for each app.
            Create a new recurring billing plan will overwrite any existing ones.
    """
    store_id  = db.StringProperty(indexed = True) # Shopify's ID for this store
    store_url = db.StringProperty(indexed = True) # must be the http://*.myshopify.com
    extra_url = db.StringProperty(indexed = True, required = False, default = '') # custom domain
    store_token = db.StringProperty(indexed = True) # Shopify token for this store

    # Recurring billing information
    recurring_billing_status     = db.StringProperty(indexed = False) # none, test, pending, accepted, denied
    recurring_billing_id         = db.IntegerProperty(indexed = False)
    recurring_billing_name       = db.StringProperty(indexed = False)
    recurring_billing_price      = db.StringProperty(indexed = False)
    recurring_billing_created    = db.DateTimeProperty(indexed = False)
    recurring_billing_trial_days = db.IntegerProperty(indexed = False)
    recurring_billing_trial_ends = db.DateTimeProperty(indexed = False)

    # One-time charge information
    charge_ids = db.ListProperty(float, indexed = False)
    charge_names = db.ListProperty(str, indexed = False)
    charge_prices = db.ListProperty(str, indexed = False)
    charge_createds = db.ListProperty(datetime.datetime, indexed = False)
    charge_statuses = db.ListProperty(str, indexed = False)

    def __init__(self, *args, **kwargs):
        super(AppShopify, self).__init__(*args, **kwargs)
        self.get_settings()

    def _validate_self(self):
        if not re.match("(http|https)://[\w\-~]+.myshopify.com", self.store_url):
            raise ValueError("<%s.%s> has malformated store url '%s'" % (self.__class__.__module__, self.__class__.__name__, self.store_url))
        return True

    def get_settings(self):
        class_name = self.class_name()
        self.settings = None 
        try:
            self.settings = SHOPIFY_APPS[class_name]
        except Exception, e:
            logging.error('could not get settings for app %s: %s' % (class_name, e))
    
    @staticmethod
    def _Shopify_str_to_datetime(dt):
        # Removes colon at 3rd to last character
        # Shopify format: YYYY-MM-DDTHH:MM:mmSHH:MM
        #                 2012-02-15T15:12:21-05:00
        # where SHH:MM is signed UTC offset hours : minutes
        time_offset = dt[-6:]
        time_without_offset = dt[:-6] 
        return datetime.datetime.strptime(time_without_offset, "%Y-%m-%dT%H:%M:%S" )
    
    @staticmethod
    def _datetime_to_Shopify_str(dt):
        # Adds colon as 3rd to last character
        # UTC format: YYYY-MM-DDTHH:MM:mmSHHMM
        # where SHHMM is signed UTC offset in hours minutes
        dts = dt.isoformat()
        return dts[:-2] + ':' + dts[-2:]
    
    # Retreivers ------------------------------------------------------------
    @classmethod
    def get_by_url(cls, store_url):
        """ Fetch a Shopify app via the store's url"""
        store_url = get_shopify_url(store_url)

        logging.info("Shopify: Looking for %s" % store_url)
        return cls.all().filter('store_url =', store_url).get()

    # Shopify API Calls ------------------------------------------------------------
    def _call_Shopify_API(self, verb, call, payload= None):
        """ Calls Shopify API

        Inputs:
            verb - <String> one of GET, POST, PUT, DELETE
            call - <String> api call
            payload - <Object> Data to send with request
        
        Returns:
            <Object> response data

            or raises ShopifyAPIError
        """
        if verb not in ['GET', 'get', 'POST', 'post',
                    'PUT', 'put', 'DELETE', 'delete']:
            raise ValueError('verb must be one of GET, POST, PUT, DELETE')
        
        url      = '%s/admin/%s' % (self.store_url, call)
        username = self.settings['api_key'] 
        password = hashlib.md5(self.settings['api_secret'] + self.store_token).hexdigest()
        header   = {'content-type':'application/json'}
        h        = httplib2.Http()
        
        # Auth the http lib
        h.add_credentials(username, password)
        
        # Make request
        resp, content = h.request(
                url,
                verb,
                body    = json.dumps(payload),
                headers = header
            )

        data = {}
        error = False

        response_actions = {
            200: lambda x: json.loads(x),
            201: lambda x: json.loads(x)
        }

        if "application/json" in resp['content-type']:
            try:
                data = response_actions.get(int(resp.status))(content)
                error = (True if data.get("errors") else False)
            except TypeError:
                error = True
        else:
            error = True

        if not error:
            return data
        else:
            #Email.emailDevTeam(
            #    '%s APPLICATION API REQUEST FAILED\nStatus:%s %s\nStore: %s\nResponse: %s' % (
            #        self.class_name(),
            #        resp.status,
            #        resp.reason,
            #        self.store_url,
            #        data if data else content
            #    )        
            #)
            raise ShopifyAPIError(resp.status, resp.reason, url + ", " + content)

    def _retrieve_single_billing_object(self, charge_type, id):
        """ Retrieve billing info for customer

        Returns: <Object> charge info
        """

        # TODO: Find out why we can't retrieve individual payments (always get 'page not found' after redirect)
        results = self._call_Shopify_API('GET', '%s.json' % charge_type)

        application_charges = results[charge_type]

        result = {}
        for charge in application_charges:
            if charge["id"] == id:
                result = charge
                break

        if result is not {}:
            return {charge_type: result}
        else:
            # TODO: Error!
            pass
    
    def setup_application_charge(self, settings):
        """ Setup one-time charge for store

        Inputs:
            settings = {
                    "price": <Number>,
                    "name": <String> app name / name on invoice,
                    "return_url": <String> redirect after store owner has confirmed/denied charges
                    ["test": <Boolean> true or false ]
                }
            Example: settings = {
                    "name": "Super Duper Expensive action",
                    "price": 100.0,
                    "return_url": "http://super-duper.shopifyapps.com",
                    "test": true
                }
        
        Returns:
            url where store owner should be redirected to confirm / deny charges
        """

        result = self._call_Shopify_API('POST', 'application_charges.json',
                                { "application_charge": settings })

        data = result["application_charge"]
        
        if data['status'] != 'pending':
            raise ShopifyBillingError("Setup of application charge was denied", data)
        
        self.charge_ids.append( data['id'] )
        self.charge_names.append( data['name'] )
        self.charge_prices.append( data['price'] )
        self.charge_createds.append( self._Shopify_str_to_datetime(data['created_at']) )
        self.charge_statuses.append('pending')

        return data['confirmation_url']
    
    def _retrieve_application_charge(self):
        """ Retrieve billing info for customer

        Returns: <Object> charge info
        """
        return self._retrieve_single_billing_object('application_charge', self.charge_id)
    
    def activate_application_charge(self, settings):
        """ Activate charge for customer that has approved it

        Note:
            First setup charge, then redirect to confirmation_url.
            Store owner's confirmation/denial hits the return_url.  return_url
            handler should activate for confirmed charge.
        
        Inputs:
            settings = {
                    "charge_id": <int> Shopify charge id,
                    "return_url": <str> url customer redirected to (this url)
                    "test": None or "true"
                }
            
            Example: settings = {
                    "charge_id": 675931192
                    "return_url": "YOUR_URL?charge_id=675931192",
                    "test": null
                }
           
        Returns:
            None
        """

        data = self._retrieve_application_charge()

        charge_data = result['application_charges']

        if charge_data == 'pending':
            # Update status
            charge_data.update({
                "status":"accepted"
            })
            charge_data.update(settings)
        
            data = self._call_Shopify_API('POST',
                        'application_charges/#%s/activate.json' % settings.charge_id,
                        { "application_charge": charge_data })
            
            if data['status'] == 'accepted':
                for i, cid in enumerate(self.charge_ids):
                    if cid == settings.charge_id:
                        self.charge_statuses[i] = "accepted"
                        break
            else:
                raise ShopifyBillingError('Charge activation denied', data)
        else:
            raise ShopifyBillingError('Charge cancelled before activation request', recurring_billing_data)
        
        return
    
    # TODO: Refactor billing common functionality
    def setup_recurring_billing(self, settings):
        """ Setup store with a recurring blling charge for this app.

        Note: 
            A Shopify store can only have 1 recuring billing plan per app.
            Setting up a new recurring billing plan will replace the older one.

        Inputs:
            settings = {
                    "price": <Number>,
                    "name": <String> app name / name on invoice,
                    "return_url": <String> redirect after store owner has confirmed/denied charges
                    ["test": <Boolean> true or false,
                     "trial_days: <Number> ]
                }
            Example: settings = {
                    "name": "Super Duper Plan",
                    "price": 10.0,
                    "return_url": "http://super-duper.shopifyapps.com",
                    "trial_days": 5,
                    "test": false
                }
        
        Returns:
            url where store owner should be redirected to confirm / deny charges
        """
        
        result = self._call_Shopify_API('POST', 'recurring_application_charges.json',
                                { "recurring_application_charge": settings })

        data = result["recurring_application_charge"]

        if data['status'] != 'pending':
            raise ShopifyBillingError("Setup of recurring billing was denied", data)
        
        self.recurring_billing_id = data['id']
        self.recurring_billing_name = data['name']
        self.recurring_billing_price = data['price']
        self.recurring_billing_created = self._Shopify_str_to_datetime(data['created_at'])
        self.recurring_billing_status = data['status']
        self.recurring_billing_trial_days = data['trial_days']

        return data['confirmation_url']
    
    def _retrieve_recurring_billing(self):
        """ Retrieve billing info for customer

        Returns: <Object> billing info
        """
        return self._retrieve_single_billing_object('recurring_application_charges', self.recurring_billing_id)
    
    def activate_recurring_billing(self, settings):
        """ Activate billing for customer that has approved it

        Note:
            First setup recurring billing, then redirect to confirmation_url.
            Store owner's confirmation/denial hits the return_url.  return_url
            handler should activate for confirmed charges.
        
        Inputs:
            settings = {
                    return_url: <String> ...
                    "test": None or "true"

                }
            
            Example: settings = {
                    "return_url": "http://yourapp.com?charge_id=455696195",
                    "test": null
                }
           
        Returns:
            None
        """
        # First retrieve most of the data from Shopify
        result = self._retrieve_recurring_billing()

        recurring_billing_data = result['recurring_application_charges']

        # Check that status isn't cancelled
        if recurring_billing_data["status"] == 'accepted':
            # Update status
            recurring_billing_data.update({
                "status":"accepted"
            })
            recurring_billing_data.update(settings)
        
            # TODO: Why can't I activate this charge?
            data = self._call_Shopify_API('POST',
                        'recurring_application_charges/#%s/activate.json' % self.recurring_billing_id,
                        { "recurring_application_charge": recurring_billing_data })
            
            if data['status'] == 'accepted':
                self.recurring_billing_status = "accepted"
            else:
                raise ShopifyBillingError('Recurring billing activation denied', data)
        else:
            raise ShopifyBillingError('Recurring billing cancelled before activation request', recurring_billing_data)
        
        return

    def queue_webhooks(self, product_hooks_too=False, webhooks=None):
        """ Determine which webhooks will have to be installed,
            and add them to the queue for parallel processing """
        # Avoids mutable default parameter [] error
        if not webhooks:
            webhooks = []

        url      = '%s/admin/webhooks.json' % self.store_url
        username = self.settings['api_key'] 
        password = hashlib.md5(self.settings['api_secret'] + self.store_token).hexdigest()
        headers  = {
            'content-type':'application/json',
            "Authorization": "Basic %s" % base64.b64encode(("%s:%s") % (username,password))
        }

        default_webhooks = [
            # Install the "App Uninstall" webhook
            { "webhook": { "address": "%s/a/shopify/webhook/uninstalled/%s/" % (URL, self.class_name()),
                           "format": "json", "topic": "app/uninstalled" }
            }
        ]

        if product_hooks_too:
            default_webhooks.extend([
                # Install the "Product Creation" webhook
                { "webhook": { "address": "%s/product/shopify/webhook/create" % ( URL ),
                               "format": "json", "topic": "products/create" }
                },
                # Install the "Product Update" webhook
                { "webhook": { "address": "%s/product/shopify/webhook/update" % ( URL ),
                               "format": "json", "topic": "products/update" }
                },
                # Install the "Product Delete" webhook
                { "webhook": { "address": "%s/product/shopify/webhook/delete" % ( URL ),
                               "format": "json", "topic": "products/delete" }
                }
            ])
        
            # See what we've already installed
            # First fetch webhooks that already exist
            data = None
            result = urlfetch.fetch(url=url, method='GET', headers=headers)
            
            if 200 <= int(result.status_code) <= 299:
                data = json.loads(result.content)
            else:
                error_msg = 'Error getting webhooks, %s: %s\n%s\n%s\n%s' % (
                    result.status_code,
                    url,
                    self.store_url,
                    result,
                    result.content
                )
                logging.error(error_msg)
                Email.emailDevTeam(error_msg)
                return
            
            # Dequeue whats already installed so we don't reinstall it
            for w in data['webhooks']:
                # Remove trailing '/'
                address = w['address'] if w['address'][-1:] != '/' else w['address'][:-1]
                
                for i, webhook in enumerate(default_webhooks):
                    if webhook['webhook']['address'] == address:
                        del(default_webhooks[i])
                        break
        
        webhooks.extend(default_webhooks)
        
        if webhooks:
            self._webhooks_url = url
            self._queued_webhooks = webhooks

    def get_script_tags(self):
        return self.__call_Shopify_API("GET", "script_tags.json")

    def uninstall_script_tags(self):
        result = self.get_script_tags()
        script_tags = result['script_tags']

        for script_tag in script_tags:
            self.__call_Shopify_API("DELETE", "script_tags/#%s.json" % script_tag["id"]);

        logging.info('uninstalled %d script_tags' % len(script_tags))

    def queue_script_tags(self, script_tags=None):
        """ Determine which script tags will have to be installed,
            and add them to the queue for parallel processing """
        if not script_tags:
            return

        self._script_tags_url = '%s/admin/script_tags.json' % self.store_url
        self._queued_script_tags = script_tags

    def queue_assets(self, assets=None):
        """ Determine which assets will have to be installed,
            and add them to the queue for parallel processing """
        if not assets:
            return
        
        username = self.settings['api_key'] 
        password = hashlib.md5(self.settings['api_secret'] + self.store_token).hexdigest()
        headers = {
            'content-type':'application/json',
            "Authorization": "Basic %s" % base64.b64encode(("%s:%s") % (username,password))
        }
        theme_url = '%s/admin/themes.json' % self.store_url
        main_id = None

        # Find out which theme is in use
        result = urlfetch.fetch(url=theme_url, method='GET', headers=headers)

        if 200 <= int(result.status_code) <= 299:
            # HTTP status 200's == success
            content = json.loads(result.content)
            for theme in content['themes']:
                if 'role' in theme and 'id' in theme:
                    if theme['role'] == 'main':
                        main_id = theme['id']
                        break
        else:
            error_msg = 'Error getting themes, %s: %s\n%s\n%s\n%s' % (
                resp.status,
                theme_url,
                self.store_url,
                resp,
                content
            )
            logging.error(error_msg)
            Email.emailDevTeam(error_msg)

        self._assets_url = '%s/admin/themes/%d/assets.json' % (self.store_url, main_id)
        self._queued_assets = assets

    def install_queued(self):
        """ Install webhooks, script_tags, and assets in parallel 
            Note: first queue everything up, then call this!
        """
        # Helper functions
        def handle_webhook_result(rpc, webhook):
            resp = rpc.get_result()
            
            if 200 <= int(resp.status_code) <= 299:
                # HTTP status 200's == success
                logging.info('Installed webhook, %s: %s' % (resp.status_code, webhook['webhook']['topic']))
            else:
                error_msg = 'Webhook install failed, %s: %s\n%s\n%s\n%s' % (
                        resp.status_code,
                        webhook['webhook']['topic'],
                        self.store_url,
                        resp.headers,
                        resp.content
                    )
                logging.error(error_msg)
                Email.emailDevTeam(error_msg)

        def handle_script_tag_result(rpc, script_tag):
            resp = rpc.get_result()

            if 200 <= int(resp.status_code) <= 299:
                # HTTP status 200's == success
                logging.info('Installed script tag, %s: %s' % (resp.status_code, script_tag['script_tag']['src']))
            else:
                error_msg = 'Script tag install failed, %s: %s\n%s\n%s\n%s' % (
                    resp.status_code,
                    script_tag['script_tag']['src'],
                    self.store_url,
                    resp,
                    content
                )
                logging.error(error_msg)
                Email.emailDevTeam(error_msg)

        def handle_asset_result(rpc, asset):
            resp = rpc.get_result()
            
            if 200 <= int(resp.status_code) <= 299:
                # HTTP status 200's == success
                logging.info('Installed asset, %s: %s' % (resp.status_code, asset['asset']['key']))
            else:
                error_msg = 'Script tag install failed, %s: %s\n%s\n%s\n%s' % (
                    resp.status_code,
                    asset['asset']['key'],
                    self.store_url,
                    resp,
                    content
                )
                logging.error(error_msg)
                Email.emailDevTeam(error_msg)

        def deadline_exceeded_catch(callback_func, **kwargs):
            try:
                callback_func(**kwargs)
            except DeadlineExceededError:
                logging.error('Installation failed, deadline exceeded:\n%s' % (
                    '\n'.join( [ "%s= %r" % (key, value) for key, value in kwargs.items() ] ) ))

        # Use a helper function to define the scope of the callback
        def create_callback(callback_func, **kwargs):
            return lambda: deadline_exceeded_catch(callback_func, **kwargs)

        rpcs = []
        username = self.settings['api_key'] 
        password = hashlib.md5(self.settings['api_secret'] + self.store_token).hexdigest()
        headers = {
            'content-type':'application/json',
            "Authorization": "Basic %s" % base64.b64encode(("%s:%s") % (username,password))
        }

        # Fire off all queued requests
        if hasattr(self, '_queued_webhooks') and hasattr(self, '_webhooks_url'):
            for webhook in self._queued_webhooks:
                rpc = urlfetch.create_rpc()
                rpc.callback = create_callback(handle_webhook_result, rpc=rpc, webhook=webhook)
                urlfetch.make_fetch_call(rpc=rpc, url=self._webhooks_url, payload=json.dumps(webhook),
                                         method='POST', headers=headers)
                rpcs.append(rpc)

        if hasattr(self, '_queued_script_tags') and hasattr(self, '_script_tags_url'):
            for script_tag in self._queued_script_tags:
                rpc = urlfetch.create_rpc()
                rpc.callback = create_callback(handle_script_tag_result, rpc=rpc, script_tag=script_tag)
                urlfetch.make_fetch_call(rpc=rpc, url=self._script_tags_url, payload=json.dumps(script_tag),
                                         method='POST', headers=headers)
            rpcs.append(rpc)

        if hasattr(self, '_queued_assets') and hasattr(self, '_assets_url'):
            for asset in self._queued_assets:
                rpc = urlfetch.create_rpc()
                rpc.callback = create_callback(handle_asset_result, rpc=rpc, asset=asset)
                urlfetch.make_fetch_call(rpc=rpc, url=self._assets_url, payload=json.dumps(asset),
                                         method='POST', headers=headers)

        # Finish all RPCs, and let callbacks process the results.
        for rpc in rpcs:
            try:
                rpc.wait()
            except DeadlineExceededError:
                rpc.callback()
        
        # All callbacks finished
        return
# end class
