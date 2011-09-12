#!/usr/bin/env python

"""
campaign processes!
"""

from google.appengine.api import memcache, taskqueue, urlfetch

from apps.campaign.models import Campaign, ShareCounter, get_campaign_by_id
from apps.user.models import * 

from util.consts import *
from util.emails import Email
from util.helpers import *
from util.urihandler import URIHandler

class CampaignClicksCounter( webapp.RequestHandler ):
    def post( self ): 
        campaign = get_campaign_by_id( self.request.get('campaign_uuid') )
        
        campaign.cached_clicks_count = 0
        if hasattr( campaign, 'links_' ):
            for l in campaign.links_:
                campaign.cached_clicks_count += l.count_clicks()

        campaign.put()

class TriggerCampaignAnalytics(webapp.RequestHandler):
    def get(self):
        scope = self.request.get('scope', 'week')
        campaigns = Campaign.all()
        for c in campaigns:
            taskqueue.add(url = '/computeCampaignAnalytics',
                          params = { 'ca_key': c.key(), 
                                      'scope'  : scope, })

class ComputeCampaignAnalytics(webapp.RequestHandler):
    """Fetch facebook information about the given user"""
    def post(self):
        rq_vars = get_request_variables(['ca_key', 'scope'], self)
        ca = db.get(rq_vars['ca_key'])
        ca.compute_analytics(rq_vars['scope'])

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

        # Send out the email.
        Email.first10Shares( email_addr )

        # Set the emailed flag.
        campaign = get_campaign_by_id( campaign_id )
        campaign.emailed_at_10 = True
        campaign.put()

