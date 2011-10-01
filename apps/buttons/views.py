#!/usr/bin/env python

import logging
from django.utils import simplejson 

from apps.buttons.models import *
from apps.link.models import get_link_by_willt_code
from apps.user.models import get_or_create_user_by_facebook
from apps.user.models import get_user_by_cookie
from apps.testimonial.models import create_testimonial

from util.urihandler import URIHandler
from util.helpers import get_request_variables

class ButtonsAction(URIHandler):
    def post(self, action, obj):
        """
        This is going to handle when a user clicks on a button and wants to do
        an action. This is assuming an oauth happened and that data was
        passed to us. Ripped from plugin/plugin.py
        """
        logging.info("We are posting to facebook")
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
                request_handler = self
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
        else:
            # got an existing user but doesn't have facebook info
            user.update(
                fb_identity = rq_vars['fb_id'],
                fb_access_token = rq_vars['fb_token']
            )

        logging.info('got user and have facebook jazz')

        link = get_link_by_willt_code(rq_vars['wcode'])

        facebook_share_id, plugin_response = user.facebook_action(
            action,
            obj,
            link.target_url
        )
        
        if link:
            link = get_link_by_willt_code(rq_vars['wcode'])
            link.app_.increment_shares()
            # add the user to the link now as we may not get a respone
            link.add_user(user)

            # Save the Testimonial
            create_testimonial(user=user, message='I %s this %s' % (action, obj), link=link)
        else:
            logging.error('could not get link')
        logging.info('sending response %s' % plugin_response)
        response_json = {
            'status': plugin_response,
            'data': {
                'id': facebook_share_id    
            }
        }
        self.response.out.write(simplejson.dumps(response_json))


class ButtonsJS(URIHandler):
    def get(self):
        # dyncamic loader for buttons
        # this will return js
        pass

class EditButtonAjax(URIHandler):
    def post(self, button_id):
        # handle posting from the edit form
        pass

class EditButton(URIHandler):
    def get(self, button_id):
        # show the edit form
        pass

class ListButtons(URIHandler):
    def get(self):
        # show the buttons enabled for this site
        client = self.get_client()
        if client:
            shop_owner = client.merchant.get_attr('full_name')
        else:
            shop_owner = 'Awesomer Bob'

        template_values = {
            'query_string': self.request.query_string,
            'shop_owner': shop_owner 
        }
        
        self.response.out.write(self.render_page('list.html', template_values))

