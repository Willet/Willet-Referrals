#!/usr/bin/env python

from apps.feedback.models import *

class DoAddFeedback( URIHandler ):
    def post( self ):
        client = self.get_client()
        msg    = self.request.get('message')
        
        feedback = Feedback( client=client, message=msg )
        feedback.put()
        
        self.redirect( '/about?thx=1' )

