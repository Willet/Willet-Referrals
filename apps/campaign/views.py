#!/usr/bin/env python
__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc."

import hashlib, re, datetime

from django.utils import simplejson as json
from gaesessions import get_current_session
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api.datastore_errors import BadValueError

from apps.client.models   import Client, get_client_by_email, authenticate, register
from apps.campaign.models import get_campaign_by_id, Campaign
from apps.feedback.models import Feedback
from apps.stats.models import Stats
from apps.user.models import User, get_user_by_cookie, get_user_by_uuid
from apps.link.models import Link
from apps.conversion.models import Conversion

from util.helpers    import *
from util.urihandler import URIHandler
from util.consts     import *


class ShowCampaignPage( URIHandler ):
    # Renders a campaign page
    def get(self, campaign_id = ''):
        #client          = self.get_client()
        #campaign_id     = self.request.get( 'id' )
        template_values = { 'campaign' : None }
        
        # Grab the campaign
        campaign = get_campaign_by_id(campaign_id)
        if campaign == None:
            self.redirect('/account')
            return
        
        campaign.compute_analytics('month')
        sms = campaign.get_reports_since('month', datetime.datetime.today() - datetime.timedelta(40), count=1)
        template_values['campaign'] = campaign
        template_values['sms'] = sms
        total_clicks = campaign.count_clicks()
        template_values['total_clicks'] = total_clicks
        results, mixpanel = campaign.get_results( total_clicks )
        
        smap = {'twitter': 0, 'linkedin': 1, 'facebook': 2, 'email': 3}

        totals = {'shares':0, 'reach' : 0, 'clicks': 0, 'conversions': 0, 'profit': 0, 'users': [], 'name':''}
        service_totals = []
        props = ['shares', 'reach', 'clicks', 'conversions', 'profit']
        while len(service_totals) < len(smap):
            service_totals.append({'shares':0, 'reach' : 0, 'clicks': 0, 'conversions': 0, 'profit': 0, 'users': [], 'name':''})
                
        for s in sms:
            row = smap[s['name']]
            service_totals[row]['name'] = s['name']
            service_totals[row]['users'].append(s['users'])
            for prop in props:
                totals[prop] += s[prop]
                service_totals[row][prop] += s[prop]
            
        template_values['results']     = results
        template_values['mixpanel']    = mixpanel
        template_values['has_results'] = len( results ) != 0
        template_values['current'] = 'campaign'

        template_values['api_key'] = MIXPANEL_API_KEY
        template_values['platform_secret'] = hashlib.md5(MIXPANEL_SECRET + campaign.uuid).hexdigest()
        template_values['totals'] = totals
        template_values['service_totals'] = service_totals
        template_values['BASE_URL'] = URL
        logging.info(service_totals) 
        self.response.out.write(self.render_page('campaign.html', template_values))

class ShowCampaignJSONPage( URIHandler ):
    # Renders a campaign page
    def get(self):
        client = self.get_client() # May be None
        campaign_id = self.request.get( 'id' )
        template_values = { 'campaign' : None }
        
        if campaign_id:
            
            # Grab the campaign
            campaign = get_campaign_by_id( campaign_id )
            if campaign == None:
                self.redirect( '/account' )
                return
            
            # Gather info to display
            total_clicks = campaign.count_clicks()
            results, foo = campaign.get_results( total_clicks )
            has_results  = len(results) != 0
            
            logging.info('results :%s' % results)
            
            # Campaign details
            template_values['campaign'] = { 'title' : campaign.title, 
                                            'product_name' : campaign.product_name,
                                            'target_url' : campaign.target_url,
                                            'blurb_title' : campaign.blurb_title,
                                            'blurb_text' : campaign.blurb_text,
                                            'share_text': campaign.share_text, 
                                            'webhook_url' : campaign.webhook_url }
            template_values['total_clicks'] = total_clicks
            template_values['has_results']  = has_results
            
            to_show = []
            for r in results:
                e = {'place' : r['num'],
                     'click_count' : r['clicks'],
                     'clicks_ratio' : r['clicks_ratio']}
                     
                if r['user']:
                    e['twitter_handle'] = r['user'].twitter_handle
                    e['user_uid'] = r['link'].supplied_user_id
                    e['twitter_followers_count'] = r['user'].twitter_followers_count
                    e['klout_score'] = r['user'].kscore
                    
                to_show.append( e )
                
            if has_results:
                template_values['results']  = to_show
        
        self.response.out.write(json.dumps(template_values))

class ShowEditPage( URIHandler ):
    # Renders a campaign page
    def get(self):
        client       = self.get_client() # may be None
        
        campaign_id  = self.request.get( 'id' )
        error        = self.request.get( 'error' )
        error_msg    = self.request.get( 'error_msg')
        title        = self.request.get( 'title' )
        product_name = self.request.get( 'product_name' )
        target_url   = self.request.get( 'target_url' )
        blurb_title  = self.request.get( 'blurb_title' )
        blurb_text   = self.request.get( 'blurb_text' )
        share_text   = self.request.get( 'share_text' )
        webhook_url  = self.request.get( 'webhook_url' ) 
        
        template_values = { 'campaign' : None }
        
        # Fake a campaign to put data in if there is an error
        
        if error == '1':
            template_values['error'] = 'Invalid url.'
            template_values['campaign'] = { 'title' : title,
                                            'product_name' : product_name,
                                            'target_url' : target_url,
                                            'blurb_title' : blurb_title,
                                            'blurb_text' : blurb_text,
                                            'share_text' : share_text, 
                                            'webhook_url' : webhook_url }
        elif error == '2':
            template_values['error'] = 'Please don\'t leave anything blank.'
            template_values['campaign'] = { 'title' : title,
                                            'product_name' : product_name,
                                            'target_url' : target_url,
                                            'blurb_title' : blurb_title,
                                            'blurb_text' : blurb_text,
                                            'share_text' : share_text, 
                                            'webhook_url' : webhook_url }
        elif error == '3':
            template_values['error'] = 'There was an error with one of your inputs: %s' % error_msg
            template_values['campaign'] = { 'title' : title,
                                            'product_name' : product_name,
                                            'target_url' : target_url,
                                            'blurb_title' : blurb_title,
                                            'blurb_text' : blurb_text,
                                            'share_text' : share_text, 
                                            'webhook_url' : webhook_url }
                                        
        # If there is no campaign_id, then we are creating a new one:
        elif campaign_id:
            
            # Updating an existing campaign here:
            campaign = get_campaign_by_id( campaign_id )
            if campaign == None:
                self.redirect( '/account' )
                return
            
            template_values['campaign'] = campaign
            
        template_values['BASE_URL'] = URL
        
        self.response.out.write(self.render_page('edit.html', template_values))

class ShowCodePage( URIHandler ):
    # Renders a campaign page
    @login_required
    def get(self, client):
        campaign_id = self.request.get( 'id' )
        template_values = { 'campaign' : None }
        
        if campaign_id:
            # Updating an existing campaign here:
            campaign = get_campaign_by_id( campaign_id )
            if campaign == None:
                self.redirect( '/account' )
                return
            
            if campaign.client == None:
                campaign.client = client
                campaign.put()
                
            template_values['campaign'] = campaign
        
        template_values['BASE_URL'] = URL
        
        self.response.out.write(self.render_page('code.html', template_values))


class DoUpdateOrCreateCampaign( URIHandler ):
    def post( self ):
        client = self.get_client() # might be None
        
        campaign_id   = self.request.get( 'uuid' )
        title        = self.request.get( 'title' )
        product_name = self.request.get( 'product_name' )
        target_url   = self.request.get( 'target_url' )
        blurb_title  = self.request.get( 'blurb_title' )
        blurb_text   = self.request.get( 'blurb_text' )
        share_text   = self.request.get( 'share_text' )
        webhook_url  = self.request.get( 'webhook_url' ) 
        
        campaign = get_campaign_by_id( campaign_id )
        
        title = title.capitalize() # caps it!
        
        if title == '' or product_name == '' or target_url == '' or blurb_title == '' or blurb_text == '' or share_text == '' or webhook_url == '':
            self.redirect( '/edit?id=%s&error=2&title=%s&blurb_title=%s&blurb_text=%s&share_text=%s&target_url=%s&product_name=%s&webhook_url=%s'
            % (campaign_id, title, blurb_title, blurb_text, share_text, target_url, product_name, webhook_url) )
            return
            
        if not isGoodURL( target_url ) or not isGoodURL( webhook_url ):
            self.redirect( '/edit?id=%s&error=1&title=%s&blurb_title=%s&blurb_text=%s&share_text=%s&target_url=%s&product_name=%s&webhook_url=%s'
            % (campaign_id, title, blurb_title, blurb_text, share_text, target_url, product_name, webhook_url) )
            return
        
        # If campaign doesn't exist,
        if campaign == None:
        
            # Create a new one!
            try:
                uuid = generate_uuid(16)
                campaign = Campaign( key_name=uuid,
                                     uuid=uuid,
                                     client=client, 
                                     title=title[:100], 
                                     product_name=product_name,
                                     target_url=target_url,
                                     blurb_title=blurb_title,
                                     blurb_text=blurb_text,
                                     share_text=share_text,
                                     webhook_url=webhook_url)
                campaign.put()
            except BadValueError, e:
                self.redirect( '/edit?error=3&error_msg=%s&id=%s&title=%s&blurb_title=%s&blurb_text=%s&share_text=%s&target_url=%s&webhook_url=%s&product_name=%s' % (str(e), campaign_id, title, blurb_title, blurb_text, share_text, target_url, webhook_url, product_name) )
                return
        
        # Otherwise, update the existing campaign.
        else:
            try:
                campaign.update( title=title[:100], 
                                 product_name=product_name,
                                 target_url=target_url,
                                 blurb_title=blurb_title, 
                                 blurb_text=blurb_text,
                                 share_text=share_text, 
                                 webhook_url=webhook_url)
            except BadValueError, e:
                self.redirect( '/edit?error=3&error_msg=%s&id=%s&title=%s&blurb_title=%s&blurb_text=%s&share_text=%s&target_url=%s&webhook_url=%s&product_name=%s' % (str(e), campaign_id, title, blurb_title, blurb_text, share_text, target_url, webhook_url, product_name) )
                return
        
        if client == None:
            self.redirect( '/login?u=/code?id=%s' % campaign.uuid )
        else:
            self.redirect( '/code?id=%s' % campaign.uuid )

class DoDeleteCampaign( URIHandler ):
    def post( self ):
        client = self.get_client()
        campaign_uuid = self.request.get( 'campaign_uuid' )
        
        logging.info('campaign id: %s' % campaign_uuid)
        campaign = get_campaign_by_id( campaign_uuid )
        if campaign.client.key() == client.key():
            logging.info('deelting')
            campaign.delete()
        
        self.redirect( '/account' )


