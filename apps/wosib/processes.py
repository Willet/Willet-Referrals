#!/usr/bin/env python

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2012, Willet, Inc"

import re

from datetime import datetime
from django.utils import simplejson as json
from google.appengine.api import taskqueue
from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import template 
from google.appengine.ext.webapp.util import run_wsgi_app

from apps.wosib.actions       import *
from apps.action.models       import UserAction
from apps.app.models          import App
from apps.app.models          import get_app_by_id
from apps.email.models        import Email
from apps.link.models         import Link
from apps.product.shopify.models import ProductShopify
from apps.product.models      import Product
from apps.user.models         import User
from apps.wosib.models        import WOSIBInstance
from apps.wosib.models        import PartialWOSIBInstance
from apps.user.actions        import UserIsFBLoggedIn
from apps.user.models         import User
from apps.user.models         import get_or_create_user_by_cookie
from apps.user.models         import get_user_by_cookie
from apps.user.models         import get_or_create_user_by_cookie

from util.consts              import *
from util.helpers             import url 
from util.helpers             import remove_html_tags
from util.strip_html          import strip_html
from util.urihandler          import URIHandler


class DoWOSIBVote(URIHandler):
    def post(self):
        # since WOSIBInstances contain more than one product, clients
        # just call DoWOSIBVote multiple time to vote on each product
        # they select. (right now, the UI permits selection of only 
        # product per vote anyway)
        instance_uuid = self.request.get('instance_uuid')
        logging.info ("instance_uuid = %s" % instance_uuid)
        product_uuid = self.request.get('product_uuid')
        
        instance = WOSIBInstance.get(instance_uuid)
        app = instance.app_
        user = get_or_create_user_by_cookie(self, app)

        # Make a Vote action for this User
        # TODO: use VoteCounter
        action = WOSIBVoteAction.create(user, instance, product_uuid)
        instance.votes += 1 # increase instance vote counter
        instance.put()

        # Tell the Asker they got a vote!
        email = instance.asker.get_attr('email')
        if email != "":
            Email.WOSIBVoteNotification(
                email, 
                instance.asker.get_full_name(), 
                instance.link.origin_domain, # cart url
                app.client.name,
                app.client.domain
        )

        # client just cares if it was HTTP 200 or 500.
        self.response.out.write('ok')

class GetExpiredWOSIBInstances(URIHandler):
    def post(self):
        return self.get()
    
    def get(self):
        """Gets a list of WOSIB instances to be expired and emails to be sent"""
        right_now = datetime.now()
        expired_instances = WOSIBInstance.all()\
                .filter('is_live =', True)\
                .filter('end_datetime <=', right_now) 

        for instance in expired_instances:
            taskqueue.add(
                url = url('RemoveExpiredWOSIBInstance'),
                params = {
                    'instance_uuid': instance.uuid    
                }
            )
        logging.info('expiring %d instances' % expired_instances.count())

class RemoveExpiredWOSIBInstance(webapp.RequestHandler):
    def post(self):
        return self.get()
    
    def get(self):
        """Updates the WOSIB instance in a transaction and then emails the user"""
        def txn(instance):
            instance.is_live = False
            instance.put()
            return instance
        
        instance = WOSIBInstance.get(self.request.get('instance_uuid'))
        if instance != None:
            result_instance = db.run_in_transaction(txn, instance)
            email = instance.asker.get_attr('email')
            if email != "":
                Email.WOSIBVoteCompletion(
                    email,
                    result_instance.asker.get_full_name(),
                    result_instance.link.get_willt_url(),
                    result_instance.product_img,
                    result_instance.get_yesses_count(),
                    result_instance.get_nos_count()
                )
        else:
            logging.error("could not get instance for uuid %s" % instance_uuid)
        logging.info('done expiring')

class TrackWOSIBShowAction(URIHandler):
    def get(self):
        """Compatibility with iframe shizz"""
        self.post()

    def post(self):
        """So javascript can track a wosib specific show actions"""
        success = False
        instance = app = user = action = None
        if self.request.get('instance_uuid'):
            instance = WOSIBInstance.get(self.request.get('instance_uuid')) 
        if self.request.get('app_uuid'):
            app = App.get(self.request.get('app_uuid')) 
        if self.request.get('user_uuid'):
            user = User.get(self.request.get('user_uuid')) 

        what = self.request.get('evnt')
        url = self.request.get('refer_url')
        if not url:
            # WOSIB doesn't have a target URL, but if refer is missing and target exists, use it
            url = self.request.get('target_url')

        try:
            logging.debug ('TrackWOSIBShowAction: user = %s, instance = %s, what = %s' % (user, instance, what))
            action_class = globals()[what]
            action = action_class.create(user, 
                    instance = instance, 
                    url = url,
                    app = app,
            )
        except Exception,e:
            logging.warn('(this is not serious) could not create class: %s' % e)
            try:
                logging.debug ('TrackWOSIBShowAction 2: user = %s, instance = %s, what = %s' % (user, instance, what))
                action = WOSIBShowAction.create(user, instance, what)
            except Exception, e:
                logging.error('this is serious: %s' % e, exc_info=True)
            else:
                logging.info('tracked action: %s' % action)
                success = True
        else:
            logging.info('tracked action: %s' % action)
            success = True

        self.response.out.write('')

class TrackWOSIBUserAction(URIHandler):
    """ For actions WITH AN INSTANCE """
    def get(self):
        """Compatibility with iframe shizz"""
        self.post()

    def post(self):
        """So javascript can track a wosib specific show actions"""
        success = False
        instance = app = user = action = None
        if self.request.get('instance_uuid'):
            instance = WOSIBInstance.get(self.request.get('instance_uuid')) 
        if self.request.get('app_uuid'):
            app = App.get(self.request.get('app_uuid'))
        if self.request.get('user_uuid'):
            user = User.get(self.request.get('user_uuid'))
        what = self.request.get('what')
        url = self.request.get('target_url')

        action = None
        try:
            action_class = globals()[what]
            action = action_class.create(user, 
                    instance = instance, 
                    url = url,
                    app = app,
            )
        except Exception,e:
            logging.warn('(this is not serious) could not create class: %s' % e)
            try:
                action = WOSIBUserAction.create(user, instance, what)
            except Exception, e:
                logging.error('this is serious: %s' % e, exc_info=True)
            else:
                logging.info('tracked action: %s' % action)
                success = True
        else:
            logging.info('tracked action: %s' % action)
            success = True

        self.response.out.write('')

class StartPartialWOSIBInstance( URIHandler ):
    def get (self):
        self.post()
    
    def post( self ):
        app     = App.get( self.request.get( 'app_uuid' ) )
        link    = Link.get_by_code( self.request.get( 'willt_code' ) )
        
        products = self.request.get( 'product_uuids' )
        logging.info ('products = %s' % products)
        user    = User.get( self.request.get( 'user_uuid' ) )
        PartialWOSIBInstance.create( user, app, link, products.split(',') )

class StartWOSIBInstance(URIHandler):
    def post(self):
        app  = App.get (self.request.get('app_uuid'))
        link = Link.get_by_code(self.request.get('willt_code')) # this is crazy
        products = self.request.get( 'product_uuids' )
        logging.info ('products = %s' % products)
        user    = User.get( self.request.get( 'user_uuid' ) )

        logging.info("Starting WOSIB instance for %s" % link.target_url )

        # defaults
        response = {
            'success': False,
            'data': {
                'instance_uuid': None,
                'message': None
            }
        }

        try:
            # Make the Instance!
            instance = app.create_instance(user, None, link)
        
            response['success'] = True
            response['data']['instance_uuid'] = instance.uuid
        except Exception,e:
            response['data']['message'] = str(e)
            logging.error('we had an error creating the instnace', exc_info=True)

        self.response.out.write(json.dumps(response))

class StartWOSIBAnalytics(URIHandler):
    # StartWOSIBAnalytics will eventually serve the same purpose as StartSIBTAnalytics
    # in SIBT: tally WOSIB actions.
    def get(self):
        self.response.out.write("No analytics yet")

class SendWOSIBFBMessages( URIHandler ):
    def post( self ):
        logging.info("TARGETTED_SHAREWOSIBONFACEBOOK")

        # Fetch arguments 
        ids       = json.loads( self.request.get( 'ids' ) )
        names     = json.loads( self.request.get( 'names' ) )
        msg       = self.request.get( 'msg' )
        app       = App.get( self.request.get('app_uuid') )
        product   = Product.get( self.request.get( 'product_uuid' ) )
        link      = Link.get_by_code( self.request.get( 'willt_code' ) )

        user      = User.get( self.request.get( 'user_uuid' ) )
        fb_token  = self.request.get('fb_access_token')
        fb_id     = self.request.get('fb_id')
        if not user:
            logging.warn('failed to get user by uuid %s' % self.request.get('user_uuid'))
            user  = get_or_create_user_by_cookie(self, app)

        logging.debug('friends %s %r' % (ids, names))
        logging.debug('msg :%s '% msg)

        # Format the product's desc for FB
        try:
            ex = '[!\.\?]+'
            product_desc = strip_html(product.description)
            parts = re.split(ex, product_desc[:150])
            product_desc = '.'.join(parts[:-1])
            if product_desc[:-1] not in ex:
                product_desc += '.'
        except:
            logging.info('could not get product description')
        
        # Check formatting of share msg
        try:
            if len( msg ) == 0:
                msg = "I'm not sure which one I should buy. What do you think?"
            if isinstance(msg, str):
                message = unicode(msg, errors='ignore')
        except:
            logging.info('error transcoding to unicode', exc_info=True)

        # defaults
        response = {
            'success': False,
            'data': {}
        }

        # first do sharing on facebook
        if fb_token and fb_id:
            logging.info('token and id set, updating user')
            user.update(
                fb_identity = fb_id,
                fb_access_token = fb_token
            ) 

        try:
            try:
                product_image = product.images[0]
            except:
                product_image = '%s/static/imgs/blank.png' % URL # blank
            fb_share_ids = user.fb_post_multiple_products_to_friends (  ids,
                                                                        names,
                                                                        msg,
                                                                        product_image,
                                                                        app.client.domain,
                                                                        link )
            logging.info('shared on facebook, got share id %s' % fb_share_ids)

            if len(fb_share_ids) > 0:
                # create the instance!
                # Make the Instance!
                instance = app.create_instance( user, None, link )
                # increment shares
                for i in ids:
                    app.increment_shares()

                Email.emailBarbara( '<p>Friends: %s %s</p><p>Successful Shares on FB: #%d</p><p>MESSAGE: %s</p><p>Instance: %s</p>' %(ids, names, len(fb_share_ids), msg, instance.uuid) )

                response['success'] = True
            
            # if it wasn't successful ...
            if len(fb_share_ids) != len(ids):
                # posting failed!
                response['data']['message'] = 'Could not post to facebook'

        except Exception,e:
            response['data']['message'] = str(e)
            logging.error('we had an error sharing on facebook', exc_info=True)

        logging.info('response: %s' % response)
        self.response.out.write(json.dumps(response))
