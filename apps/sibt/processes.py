#!/usr/bin/env python

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc"

import re

from django.utils import simplejson as json
from google.appengine.api import taskqueue
from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import template 
from google.appengine.ext.webapp.util import run_wsgi_app

from apps.sibt.actions        import *
from apps.action.models import UserAction
from apps.app.models          import App
from apps.app.models import get_app_by_id
from apps.email.models        import Email
from apps.link.models         import get_link_by_willt_code
from apps.product.shopify.models      import ProductShopify
from apps.product.models      import Product
from apps.user.models         import User
from apps.sibt.models         import SIBTInstance
from apps.sibt.models         import PartialSIBTInstance
from apps.testimonial.models  import create_testimonial
from apps.user.models         import User, get_or_create_user_by_cookie, get_user_by_cookie, get_user_by_uuid

from util.consts              import *
from util.helpers             import url 
from util.helpers             import remove_html_tags
from util.urihandler          import URIHandler
from util.strip_html import strip_html

class ShareSIBTInstanceOnFacebook(URIHandler):
    def post(self):
        logging.info("SHARESIBTONFACEBOOK")

        user = User.get(self.request.get('user_uuid'))
        if not user:
            logging.warn('failed to get user by uuid %s' % self.request.get('user_uuid'))
            user = get_or_create_user_by_cookie(self)
        app  = get_app_by_id(self.request.get('app_uuid'))
        willt_code = self.request.get('willt_code')
        link = get_link_by_willt_code(willt_code)
        img = self.request.get('product_img')
        product_name = self.request.get('name')
        product_desc = None 
        product_id = self.request.get('product_id')
        motivation = self.request.get('motivation')
        fb_token = self.request.get('fb_token')
        fb_id = self.request.get('fb_id')
        message = self.request.get('msg')

        product = None
        try:
            product = ProductShopify.get_by_shopify_id( str(product_id) )
        except:
            logging.info('Could not get product by id %s' % product_id, exc_info=True)
        try:
            #product_desc = '.'.join(product.description[:150].split('.')[:-1]) + '.'
            #product_desc = remove_html_tags(product_desc)
            ex = '[!\.\?]+'
            product_desc = strip_html(product.description)
            parts = re.split(ex, product_desc[:150])
            product_desc = '.'.join(parts[:-1])
            if product_desc[:-1] not in ex:
                product_desc += '.'
        except:
            logging.info('could not get product description')
        
        try:
            if isinstance(message, str):
                message = unicode(message, errors='ignore')

            if isinstance(img, str):
                img = unicode(img, errors='ignore')
            
            if isinstance(product_name, str):
                product_name = unicode(product_name, errors='ignore')

            if isinstance(product_desc, str):
                product_desc = unicode(product_desc, errors='ignore')
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
        if not hasattr(user, 'fb_access_token') or \
            not hasattr(user, 'fb_identity'):
            logging.info('Setting users facebook info')    
            user.update(
                fb_identity = fb_id,
                fb_access_token = fb_token
            ) 

        try:
            facebook_share_id, plugin_response = user.facebook_share(
                message,
                img,
                product_name,
                product_desc,
                link
            )
            logging.info('shared on facebook, got share id and response %s %s' % (
                facebook_share_id,
                plugin_response
            ))

            # if it wasn't successful ...
            if facebook_share_id == None or plugin_response == 'fail':
                # posting failed!
                response['data']['message'] = 'Could not post to facebook'
            else:
                # create the instance!
                # Make the Instance!
                instance = app.create_instance(user, 
                        None, link, img, motivation=motivation, 
                        dialog="ConnectFB")
        
                # increment link stuff
                link.app_.increment_shares()
                link.add_user(user)
                logging.info('incremented link and added user')

                # add testimonial
                create_testimonial(user=user, message=message, link=link)

                response['success'] = True
        except Exception,e:
            response['data']['message'] = str(e)
            logging.error('we had an error sharing on facebook', exc_info=True)

        logging.info('response: %s' % response)
        self.response.out.write(json.dumps(response))

class StartSIBTInstance(URIHandler):
    def post(self):
        user = get_or_create_user_by_cookie(self)
        app  = get_app_by_id(self.request.get('app_uuid'))
        link = get_link_by_willt_code(self.request.get('willt_code'))
        img = self.request.get('product_img')
        
        logging.info("Starting SIBT instance for %s" % link.target_url )

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
            instance = app.create_instance(user, None, link, img, 
                                           motivation=None, dialog="ConnectFB")
        
            response['success'] = True
            response['data']['instance_uuid'] = instance.uuid
        except Exception,e:
            response['data']['message'] = str(e)
            logging.error('we had an error creating the instnace', exc_info=True)

        self.response.out.write(json.dumps(response))

class DoVote( URIHandler ):
    def post(self):
        #user = get_or_create_user_by_cookie( self )
        
        user_uuid = self.request.get('user_uuid')
        if user_uuid != None:
            user = User.all().filter('uuid =', user_uuid).get() 

        which = self.request.get( 'which' )
        instance_uuid = self.request.get( 'instance_uuid' )
        instance = SIBTInstance.get( instance_uuid )
        app = instance.app_

        # Make a Vote action for this User
        action = SIBTVoteAction.create( user, instance, which )

        # Count the vote.
        if which.lower() == "yes":
            instance.increment_yesses()
        else:
            instance.increment_nos()

        # Tell the Asker they got a vote!
        email = instance.asker.get_attr('email')
        if email != "":
            Email.SIBTVoteNotification(
                email, 
                instance.asker.get_full_name(), 
                which, 
                instance.link.get_willt_url(), 
                instance.product_img,
                app.client.name,
                app.client.domain
            ) 

        self.response.out.write('ok')

class GetExpiredSIBTInstances(URIHandler):
    def post(self):
        return self.get()
    
    def get(self):
        """Gets a list of SIBT instances to be expired and emails to be sent"""
        from datetime import datetime
        right_now = datetime.now()
        expired_instances = SIBTInstance.all()\
                .filter('is_live =', True)\
                .filter('end_datetime <=', right_now) 

        for instance in expired_instances:
            taskqueue.add(
                url = url('RemoveExpiredSIBTInstance'),
                params = {
                    'instance_uuid': instance.uuid    
                }
            )
        logging.info('expiring %d instances' % expired_instances.count())

class RemoveExpiredSIBTInstance(webapp.RequestHandler):
    def post(self):
        return self.get()
    
    def get(self):
        """Updates the SIBT instance in a transaction and then emails the user"""
        def txn(instance):
            instance.is_live = False
            instance.put()
            return instance
        
        instance_uuid = self.request.get('instance_uuid')
        instance = SIBTInstance.get(instance_uuid)
        if instance != None:
            result_instance = db.run_in_transaction(txn, instance)
            email = instance.asker.get_attr('email')
            if email != "":
                Email.SIBTVoteCompletion(
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

class StoreAnalytics( URIHandler ):
    def get( self ):
        user = get_user_by_uuid( self.request.get('user_uuid') )

        event  = self.request.get('evnt')
        target = self.request.get( 'target_url' )
        app    = get_app_by_id( self.request.get( 'app_uuid' ) )

        # Now, tell Mixpanel
        app.storeAnalyticsDatum( event, user, target )
        logging.error('WE SHOULDNT BE DOING THIS ANYMORE, BAD PROGRAMMER')

class TrackSIBTShowAction(URIHandler):
    def get(self):
        """Compatibility with iframe shizz"""
        self.post()

    def post(self):
        """So javascript can track a sibt specific show actions"""
        success = False
        instance = app = user = action = None
        if self.request.get('instance_uuid'):
            instance = SIBTInstance.get(self.request.get('instance_uuid')) 
        if self.request.get('app_uuid'):
            app = App.get(self.request.get('app_uuid'))         
        if self.request.get('user_uuid'):
            user = User.get(self.request.get('user_uuid')) 
        what = self.request.get('evnt')
        url = self.request.get('target_url')
        try:
            action_class = globals()[what]
            action = action_class.create(user, 
                    instance=instance, 
                    url=url,
                    app=app
            )
        except Exception,e:
            logging.warn('(this is not serious) could not create class: %s' % e)
            try:
                action = SIBTShowAction.create(user, instance, what)
            except Exception, e:
                logging.error('this is serious: %s' % e, exc_info=True)
            else:
                logging.info('tracked action: %s' % action)
                success = True
        else:
            logging.info('tracked action: %s' % action)
            success = True

        self.response.out.write('')

class TrackSIBTUserAction(URIHandler):
    def get(self):
        """Compatibility with iframe shizz"""
        self.post()

    def post(self):
        """So javascript can track a sibt specific show actions"""
        success = False
        instance = app = user = action = None
        if self.request.get('instance_uuid'):
            instance = SIBTInstance.get(self.request.get('instance_uuid')) 
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
                    instance=instance, 
                    url=url,
                    app=app
            )
        except Exception,e:
            logging.warn('(this is not serious) could not create class: %s' % e)
            try:
                action = SIBTUserAction.create(user, instance, what)
            except Exception, e:
                logging.error('this is serious: %s' % e, exc_info=True)
            else:
                logging.info('tracked action: %s' % action)
                success = True
        else:
            logging.info('tracked action: %s' % action)
            success = True

        self.response.out.write('')


class StartPartialSIBTInstance( URIHandler ):
    def get( self ):
        app     = App.get( self.request.get( 'app_uuid' ) )
        link    = get_link_by_willt_code( self.request.get( 'willt_code' ) )
        product = Product.get( self.request.get( 'product_uuid' ) )
        user    = User.get( self.request.get( 'user_uuid' ) )

        PartialSIBTInstance.create( user, app, link, product )
