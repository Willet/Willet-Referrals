#!/usr/bin/env python

from util.urihandler import *
from util.helpers import *
from util.consts import *

from apps.feedback.models import Feedback

class AddFeedback(URIHandler):
    def post(self):
        client = self.get_client()
        msg    = self.request.get('message')
        
        feedback = Feedback(client=client, message=msg )
        feedback.put()
        
        self.redirect(url('ShowAboutPage', qs={'thx':1}))

