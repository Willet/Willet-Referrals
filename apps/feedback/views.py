#!/usr/bin/env python

from util.urihandler import *
from util.helpers import *
from util.consts import *

from google.appengine.api import taskqueue

from apps.feedback.models import Feedback

class AddFeedback(URIHandler):
    def post(self):
        client = self.get_client()
        msg    = self.request.get('message')
        client_id = None

        if client:
            client_id = client.uuid


        taskqueue.add(
            url = url('AddFeedbackTask'), 
            params = {
                'client_id': client_id, 
                'message': msg
            }
        )
 
        self.redirect(url('ShowAboutPage', qs={'thx':1}))

