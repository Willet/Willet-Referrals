#!/usr/bin/env python

from apps.feedback.models import *
from util.urihandler import URIHandler

class DoAddFeedback( URIHandler ):
    def post( self ):
        client = self.get_client()
        msg    = self.request.get('message')
        
        feedback = Feedback( client=client, message=msg )
        feedback.put()
        
        self.redirect( '/about?thx=1' )

