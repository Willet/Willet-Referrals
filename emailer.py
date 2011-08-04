#!/usr/bin/python

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc"

import re
import urllib

from google.appengine.api.mail import EmailMessage
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.api import taskqueue
from google.appengine.ext.webapp.util import run_wsgi_app

from models.client      import Client
from models.campaign    import Campaign, get_campaign_by_id
from util.helpers       import *
from util.urihandler    import URIHandler
from util.consts        import *

class EmailerCron( URIHandler ):

    @admin_required
    def get( self, admin ):
        campaigns = Campaign.all()

        for c in campaigns:
            #logging.info("Working on %s" % c.title)

            if not c.emailed_at_10 and c.client:
                #logging.info('count %s' % c.get_shares_count() )
                if c.get_shares_count() >= 10:

                    taskqueue.add( queue_name='emailer', 
                                   url='/emailerQueue', 
                                   name= 'EmailingCampaign%s' % c.uuid,
                                   params={'campaign_id' : c.uuid,
                                           'email' : c.client.email} )

class EmailerQueue( URIHandler ):

    @admin_required
    def post( self, admin ):
        email_addr  = self.request.get('email')
        campaign_id = self.request.get('campaign_id')

        body = template.render(os.path.join(os.path.dirname(__file__), 'templates/email.html'), {'campaign_id': campaign_id})
        to_addr =  email_addr
        subject = '[Willet Social] We Have Some Results!'
        
        e = EmailMessage(sender="Barbara@wil.lt", to=email_addr, subject=subject, html=body)
        e.send()

        # Set the emailed flag.
        campaign = get_campaign_by_id( campaign_id )
        campaign.emailed_at_10 = True
        campaign.put()
##-----------------------------------------------------------------------------##
##------------------------- The URI Router ------------------------------------##
##-----------------------------------------------------------------------------##
def main():
    application = webapp.WSGIApplication([
        (r'/emailerCron', EmailerCron),
        (r'/emailerQueue', EmailerQueue),
        ], debug=USING_DEV_SERVER)
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
