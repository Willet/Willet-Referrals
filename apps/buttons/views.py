#!/usr/bin/env python

import logging
from django.utils import simplejson 

from apps.buttons.actions   import WantAction
from apps.buttons.models    import *
from apps.link.models       import get_link_by_willt_code
from apps.testimonial.models import create_testimonial
from apps.user.models       import get_or_create_user_by_facebook
from apps.user.models       import get_user_by_cookie

from util.helpers           import get_request_variables
from util.urihandler        import URIHandler

class ButtonsAction(URIHandler):
    def post(self, action, obj):
        """
        This is going to handle when a user clicks on a button and wants to do
        an action. This is assuming an oauth happened and that data was
        passed to us. Ripped from plugin/plugin.py
        """
        logging.info("We are posting to facebook")
        logging.info("%s %s %s" % (self.request.get('wcode'), self.request.get('fb_token'), self.request.get('fb_id')))
        rq_vars = get_request_variables([
                'wcode',
                'fb_token',
                'fb_id'
            ], 
            self
        )
        user = get_user_by_cookie(self)
        if user is None:
            logging.info("creating a new user")
            user = get_or_create_user_by_facebook(
                rq_vars['fb_id'],
                token = rq_vars['fb_token'],
                request_handler = self,
                app = None # TODO: FIX THIS.
            )
        elif hasattr(user, 'fb_access_token') and hasattr(user, 'fb_identity'):
            # if the user already exists and has both
            # a fb access token and id, let's check to make sure
            # it is the same info as we just got
            if user.fb_access_token != rq_vars['fb_token'] or\
                    user.fb_identity != rq_vars['fb_id']:
                logging.error('existing users facebook information did not\
                    match new data. overwriting old data!')
                logging.error('user: %s' % user)

                # got an existing user but doesn't have facebook info
                user.update(
                    fb_identity     = rq_vars['fb_id'],
                    fb_access_token = rq_vars['fb_token']
                )
        else:
            # got an existing user but doesn't have facebook info
            user.update(
                fb_identity     = rq_vars['fb_id'],
                fb_access_token = rq_vars['fb_token']
            )

        logging.info('got user and have facebook jazz')

        link = get_link_by_willt_code(rq_vars['wcode'])

        # Send the action to FB
        facebook_share_id, plugin_response = user.facebook_action(
            action,
            obj,
            link.target_url
        )
        
        # If the 'want' is successful:
        if plugin_response == True:
            if link:
                # Store the want action
                WantAction.create( user, link.app_, link )
                
                link.app_.increment_shares()
                
                # add the user to the link now as we may not get a respone
                link.add_user(user)

                # Save the Testimonial
                create_testimonial(user=user, message='I %s this %s' % (action, obj), link=link)
            else:
                logging.error('could not get link')
        
        # Tell the JS what happened!
        logging.info('sending response %s' % plugin_response)
        response_json = {
            'status': str(plugin_response),
            'data': {
                'id': facebook_share_id    
            }
        }
        self.response.out.write(simplejson.dumps(response_json))
