#!/usr/bin/env python

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc"

from datetime import datetime 
from datetime import timedelta

from google.appengine.ext import webapp
from google.appengine.ext.webapp import template, db, webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import taskqueue

from apps.action.models       import create_sibt_vote_action
from apps.app.models          import get_app_by_id
from apps.email.models        import Email
from apps.link.models         import get_link_by_willt_code
from apps.sibt.models         import get_sibt_instance_by_uuid, get_sibt_instance_by_asker_for_url
from apps.sibt.models         import SIBTInstance
from apps.user.models         import User, get_or_create_user_by_cookie

from util.urihandler          import URIHandler
from util.consts              import *
from util.helpers import url 

class StartInstance( URIHandler ):
    def post( self ):
        user = get_or_create_user_by_cookie( self )
        app  = get_app_by_id( self.request.get('app_uuid') )
        link = get_link_by_willt_code( self.request.get('willt_code') )
        img = self.request.get('product_img')
        
        now = datetime.now()
        six_hours = timedelta(hours=6)
        end = now + six_hours

        # Make the Instance!
        instance = app.create_instance(user, end, link, img)
        
        if hasattr('user', fb_identity):
            taskqueue.add(
                url = url('FetchFacebookData'),
                params = {
                    'fb_id': self.fb_identity
                }
            )

        self.response.out.write( instance.uuid ) # give back to script.

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

class RemoveExpiredSIBTInstance(webapp.RequestHandler):
    def post(self):
        """Updates the SIBT instance in a transaction and then emails the user"""
        def txn(instance):
            instance.is_live = False
            instance.put()
            return instance
        
        rq = get_request_variables(['instance_uuid'], self) 
        instance = SIBTInstance.all()\
                .filter('uuid =', rq['instance_uuid'])\
                .get()
        if instance != None:
            result_instance = db.run_in_transaction(txn, instance)
            email = instance.asker.get_attr('email')
            if email != "":
                SIBTVoteCompletion(
                    email,
                    result_instance.asker.get_full_name(),
                    result_instance.link.get_willt_url(),
                    result_instance.product_img,
                    result_instance.get_yesses_count(),
                    result_instance.get_nos_count()
                )
        else:
            logging.error(
                    "could not get instance for uuid %" % 
                    rq['instance_uuid']
            )
        logging.info('done expiring')

