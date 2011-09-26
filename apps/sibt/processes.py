#!/usr/bin/env python

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc"

from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

from apps.action.models       import create_sibt_vote_action
from apps.app.models          import get_app_by_id
from apps.link.models         import get_link_by_willt_code
from apps.sibt.models         import get_sibt_instance_by_uuid, get_sibt_instance_by_asker_for_url
from apps.user.models         import get_or_create_user_by_cookie

from util.urihandler          import URIHandler
from util.consts              import *

class StartInstance( URIHandler ):
    
    def post( self ):
        user = get_or_create_user_by_cookie( self )

        app  = get_app_by_id( self.request.get('app_uuid') )
        link = get_link_by_willt_code( self.request.get('willt_code') )

        # Make the Instance!
        instance = app.create_instance( user, None, link )

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

        self.response.out.write( 'ok' );
