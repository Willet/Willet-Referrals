#!/usr/bin/python

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc."

import hashlib, re, datetime

from django.utils import simplejson as json
from gaesessions import get_current_session
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api.datastore_errors import BadValueError

from models.client   import Client, get_client_by_email, authenticate, register
from models.campaign import get_campaign_by_id, Campaign
from models.feedback import Feedback
from models.stats    import Stats
from models.user     import User, get_user_by_cookie, get_user_by_uuid
from models.link     import Link
from models.conversion import Conversion
from util.helpers    import *
from util.urihandler import URIHandler
from util.consts     import *
##-----------------------------------------------------------------------------##
##------------------------- The Shows -----------------------------------------##
##-----------------------------------------------------------------------------##

class ShowDashboardTestPage(URIHandler):
    def get(self):
        template_values = {}
        self.response.out.write(self.render_page('dashboard/backup_base.html', template_values))

##-----------------------------------------------------------------------------##
##------------------------- The URI Router ------------------------------------##
##-----------------------------------------------------------------------------##
def main():
    application = webapp.WSGIApplication([
        
        (r'/dashboard/test', ShowDashboardTestPage),
        (r'/demo(.*)',ShowDemoSitePage),

        

        (r'/()', ShowLandingPage)
        
        ], debug=USING_DEV_SERVER)
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
