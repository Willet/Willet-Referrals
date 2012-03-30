#!/usr/bin/python

# The AppShopify Model
# A parent class for all Shopify social 'apps'

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc"

import hashlib, datetime

from django.utils         import simplejson as json
from google.appengine.ext import db

from apps.app.models    import App
from apps.email.models  import Email

from util               import httplib2
from util.consts        import *
from util.errors        import ShopifyAPIError, ShopifyBillingError
from util.model         import Model


NUM_SHARE_SHARDS = 15

class AppShopify(Model):
    """

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
    # Shopify's ID for this store
    store_id  = db.StringProperty(indexed = True)
    
    store_url = db.StringProperty(indexed = True)

    # Shopify's token for this store
    store_token = db.StringProperty(indexed = True)

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
    
    def get_settings(self):
        class_name = self.class_name()
        self.settings = None 
        try:
            self.settings = SHOPIFY_APPS[class_name]
        except Exception, e:
            logging.error('could not get settings for app %s: %s' % (
                    class_name,
                    e
                )
            )
    
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

        # TODO: Check that no 'errors' key exists

        # Good responses
        valid_response_codes = [200, 201]
        if "application/json" in resp['content-type'] and int(resp.status) in valid_response_codes:
            data = json.loads(content)
            return data
        
        # Bad responses
        else:
            data = None
            if content:
                try:
                    data = json.loads(content)
                    return data
                except:
                    pass

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

    def install_webhooks(self, product_webhooks_too= False, webhooks= None):
        """ Install the webhooks into the Shopify store """
        # pass extra webhooks as a list
        if webhooks == None:
            webhooks = []

        logging.info("TOKEN %s" % self.store_token )
        url      = '%s/admin/webhooks.json' % self.store_url
        username = self.settings['api_key'] 
        password = hashlib.md5(self.settings['api_secret'] + self.store_token).hexdigest()
        header   = {'content-type':'application/json'}
        h        = httplib2.Http()
        
        # Auth the http lib
        h.add_credentials(username, password)
        
        # See what we've already installed and flag it so we don't double install
        if product_hooks_too:
            # First fetch webhooks that already exist
            resp, content = h.request( url, "GET", headers = header)
            data = json.loads( content ) 
            #logging.info('%s %s' % (resp, content))

            product_create = product_delete = product_update = True
            for w in data['webhooks']:
                #logging.info("checking %s"% w['address'])
                if w['address'] == '%s/product/shopify/webhook/create' % URL or \
                   w['address'] == '%s/product/shopify/webhook/create/' % URL:
                    product_create = False
                if w['address'] == '%s/product/shopify/webhook/delete' % URL or \
                   w['address'] == '%s/product/shopify/webhook/delete/' % URL:
                    product_delete = False
                if w['address'] == '%s/product/shopify/webhook/update' % URL or \
                   w['address'] == '%s/product/shopify/webhook/update/' % URL:
                    product_update = False
        
        # If we don't want to install the product webhooks, 
        # flag all as "already installed"
        else:
            product_create = product_delete = product_update = False

        # Install the "App Uninstall" webhook
        data = {
            "webhook": {
                "address": "%s/a/shopify/webhook/uninstalled/%s/" % (
                    URL,
                    self.class_name()
                ),
                "format": "json",
                "topic": "app/uninstalled"
            }
        }
        webhooks.append(data)

        # Install the "Product Creation" webhook
        data = {
            "webhook": {
                "address": "%s/product/shopify/webhook/create" % ( URL ),
                "format" : "json",
                "topic"  : "products/create"
            }
        }
        if product_create:
            webhooks.append(data)
        
        # Install the "Product Update" webhook
        data = {
            "webhook": {
                "address": "%s/product/shopify/webhook/update" % ( URL ),
                "format" : "json",
                "topic"  : "products/update"
            }
        }
        if product_update:
            webhooks.append(data)

        # Install the "Product Delete" webhook
        data = {
            "webhook": {
                "address": "%s/product/shopify/webhook/delete" % ( URL ),
                "format" : "json",
                "topic"  : "products/delete"
            }
        }
        if product_delete:
            webhooks.append(data)

        for webhook in webhooks:
            logging.info('Installing extra hook %s' % webhook)
            logging.info("POSTING to %s %r " % (url, webhook))
            resp, content = h.request(
                url,
                "POST",
                body = json.dumps(webhook),
                headers = header
            )
            logging.info('%r %r' % (resp, content)) 
            if int(resp.status) == 401:
                Email.emailDevTeam(
                    '%s WEBHOOK INSTALL FAILED\n%s\n%s\n%s' % (
                        self.class_name(),
                        resp,
                        self.store_url,
                        content
                    )        
                )
        logging.info('installed %d webhooks' % len(webhooks))

    def get_script_tags(self):
        return self.__call_Shopify_API("GET", "script_tags.json")
    
    def install_script_tags(self, script_tags=None):
        """ Install our script tags onto the Shopify store """
        if script_tags == None:
            script_tags = []

        # TODO: Remove cruft if __call_Shopify_API works

        #url      = '%s/admin/script_tags.json' % self.store_url
        #username = self.settings['api_key'] 
        #password = hashlib.md5(self.settings['api_secret'] + self.store_token).hexdigest()
        #header   = {'content-type':'application/json'}
        #h        = httplib2.Http()
        
        #h.add_credentials(username, password)
        
        for script_tag in script_tags:
            self.__call_Shopify_API("POST", "script_tags.json", payload=script_tag);
            #logging.info("POSTING to %s %r " % (url, script_tag) )
            #resp, content = h.request(
            #    url,
            #    "POST",
            #    body = json.dumps(script_tag),
            #    headers = header
            #)
            #logging.info('%r %r' % (resp, content))
            #if int(resp.status) == 401:
            #    Email.emailDevTeam(
            #        '%s SCRIPT_TAGS INSTALL FAILED\n%s\n%s' % (
            #            self.class_name(),
            #            resp,
            #            content
            #        )        
            #    )
        logging.info('installed %d script_tags' % len(script_tags))

    def uninstall_script_tags(self):
        result = self.get_script_tags()
        script_tags = result['script_tags']

        for script_tag in script_tags:
            self.__call_Shopify_API("DELETE", "script_tags/#%s.json" % script_tag["id"]);

        logging.info('uninstalled %d script_tags' % len(script_tags))

    def install_assets(self, assets=None):
        """Installs our assets on the client's store
            Must first get the `main` template in use"""
        username = self.settings['api_key'] 
        password = hashlib.md5(self.settings['api_secret'] + self.store_token).hexdigest()
        header   = {'content-type':'application/json'}
        h        = httplib2.Http()
        h.add_credentials(username, password)
        
        main_id = None

        if assets == None:
            assets = []

        # get the theme ID
        theme_url = '%s/admin/themes.json' % self.store_url
        logging.info('Getting themes %s' % theme_url)
        resp, content = h.request(theme_url, 'GET', headers = header)

        if int(resp.status) == 200:
            # we are okay
            content = json.loads(content)
            for theme in content['themes']:
                if 'role' in theme and 'id' in theme:
                    if theme['role'] == 'main':
                        main_id = theme['id']
                        break
        else:
            logging.error('%s error getting themes: \n%s\n%s' % (
                self.class_name(),
                resp,
                content
            ))
            return

        # now post all the assets
        url = '%s/admin/themes/%d/assets.json' % (self.store_url, main_id)
        for asset in assets: 
            logging.info("POSTING to %s %r " % (url, asset) )
            resp, content = h.request(
                url,
                "PUT",
                body = json.dumps(asset),
                headers = header
            )
            logging.info('%r %r' % (resp, content))
            if int(resp.status) != 200: 
                Email.emailDevTeam(
                    '%s SCRIPT_TAGS INSTALL FAILED\n%s\n%s' % (
                        self.class_name(),
                        resp,
                        content
                    )        
                )

        logging.info('installed %d assets' % len(assets))

