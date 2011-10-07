#!/usr/bin/env python

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc"

from datetime import datetime 
from datetime import timedelta

from django.utils import simplejson as json
from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import template 
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import taskqueue

from apps.action.models       import create_sibt_vote_action
from apps.app.models          import get_app_by_id
from apps.email.models        import Email
from apps.link.models         import get_link_by_willt_code
from apps.sibt.models         import get_sibt_instance_by_uuid, get_sibt_instance_by_asker_for_url
from apps.sibt.models         import SIBTInstance
from apps.testimonial.models import create_testimonial
from apps.user.models         import User, get_or_create_user_by_cookie

from util.urihandler          import URIHandler
from util.consts              import *
from util.helpers import url 

class ShareSIBTInstanceOnFacebook(URIHandler):
    def post(self):
        user = get_or_create_user_by_cookie(self)
        app  = get_app_by_id(self.request.get('app_uuid'))
        willt_code = self.request.get('willt_code')
        link = get_link_by_willt_code(willt_code)
        img = self.request.get('product_img')
        product_name = self.request.get('name')
        product_desc = self.request.get('desc')
        fb_token = self.request.get('fb_token')
        fb_id = self.request.get('fb_id')
        message = self.request.get('msg')

        # defaults
        response = {
            'success': False,
            'data': {}
        }

        # first do sharing on facebook
        if not hasattr(user, 'fb_access_token') or \
            not hasattr(user, 'fb_identity'):
            logging.info('Settin) users facebook info')    
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
                instance = app.create_instance(user, None, link, img)
        
                taskqueue.add(
                    queue_name = 'mixpanel', 
                    url = url('SendActionToMixpanel'), 
                    params = {
                        'event': 'SIBTInstanceCreated', 
                        'app': app.uuid,
                        'user': user.get_name_or_handle(),
                        'taret_url': instance.url,
                        'user_uuid': user.uuid,
                        'client': app.client.email
                    }
                )

                # increment link stuff
                link.app_.increment_shares()
                link.add_user(user)
                logging.info('incremented link and added user')

                # add testimonial
                create_testimonial(user=user, message=message, link=link)

                taskqueue.add(
                    url = url('FetchFacebookData'),
                    params = {
                        'fb_id': user.fb_identity
                    }
                )

                taskqueue.add(
                    queue_name = 'mixpanel', 
                    url = url('SendActionToMixpanel'), 
                    params = {
                        'event': 'SIBTInstanceSharedOnFacebook', 
                        'app': app.uuid,
                        'user': user.get_name_or_handle(),
                        'taret_url': link.target_url,
                        'user_uuid': user.uuid,
                        'client': app.client.email
                    }
                )
                response['success'] = True
        except Exception,e:
            response['data']['message'] = str(e)
            logging.error('we had an error sharing on facebook', exc_info=True)

        self.response.out.write(json.dumps(response))

class StartSIBTInstance(URIHandler):
    def post(self):
        user = get_or_create_user_by_cookie(self)
        app  = get_app_by_id(self.request.get('app_uuid'))
        link = get_link_by_willt_code(self.request.get('willt_code'))
        img = self.request.get('product_img')

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
            instance = app.create_instance(user, None, link, img)
        
            taskqueue.add(
                queue_name = 'mixpanel', 
                url = url('SendActionToMixpanel'), 
                params = {
                    'event': 'SIBTInstanceCreated', 
                    'app': app.uuid,
                    'user': user.get_name_or_handle(),
                    'taret_url': instance.url,
                    'user_uuid': user.uuid,
                    'client': app.client.email
                }
            )

            response['success'] = True
            response['data']['instance_uuid'] = instance.uuid
        except Exception,e:
            response['data']['message'] = str(e)
            logging.error('we had an error creating the instnace', exc_info=True)

        self.response.out.write(json.dumps(response))

class DoVote( URIHandler ):
    def post( self ):
        user = get_or_create_user_by_cookie( self )

        which = self.request.get( 'which' )
        instance_uuid = self.request.get( 'instance_uuid' )
        instance = get_sibt_instance_by_uuid( instance_uuid )

        # Make a Vote action for this User
        action = create_sibt_vote_action( user, instance )

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
                instance.product_img
            ) 

        self.response.out.write('ok')

class GetExpiredSIBTInstances(URIHandler):
    def post(self):
        return self.get()
    
    def get(self):
        """Gets a list of SIBT instances to be expired and emails to be sent"""
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
        instance = SIBTInstance.all()\
                .filter('uuid =', instance_uuid)\
                .get()
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
            logging.error (
                    "could not get instance for uuid %" % 
                    instance_uuid
            )
        logging.info('done expiring')

