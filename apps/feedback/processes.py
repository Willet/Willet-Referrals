#!/usr/bin/env python

# add user feedback
import logging

from google.appengine.ext.db import run_in_transaction 
from google.appengine.ext import webapp

from apps.feedback.models import Feedback
from apps.client.models import Client

from util.helpers import *

class AddFeedbackTask(webapp.RequestHandler):
    """Save user feedback"""
    def post(self):
        def txn(client, message):
            feedback = None
            feedback = Feedback(client=client, message=message)
            feedback.put()
            return feedback 

        rq_vars = get_request_variables(['client_id', 'message'], self)
        client = Client.all().filter('uuid =', rq_vars['client_id']).get()
        message = rq_vars['message']
        feedback = run_in_transaction(txn, client, message)

        if feedback == None:
            logging.error('error creating feedback: %s\n%s' % (client, message))


