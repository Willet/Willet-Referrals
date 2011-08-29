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

from util.helpers    import *
from util.urihandler import URIHandler
from util.consts     import *

##-----------------------------------------------------------------------------##
##-------------------------- Landing ------------------------------------------##
##-----------------------------------------------------------------------------##

class ShowLandingPage( URIHandler ):
    # Renders the main template
    def get(self, page):
        stats = Stats.all().get()
        
        template_values = { 'campaign_results' : stats.landing if stats else '' }
        
        self.response.out.write(self.render_page('landing.html', template_values))

class ShowAboutPage( URIHandler ):
    # Renders the main template
    def get(self):
        thx = self.request.get('thx')
        
        template_values = { 'thanks' : True if thx == '1' else False }
        
        self.response.out.write(self.render_page('about.html', template_values))

class ShowContactPage( URIHandler ):
    # Renders the main template
    def get(self):
        template_values = []
        
        self.response.out.write(self.render_page('contact.html', template_values))

class ShowLoginPage( URIHandler ):
    # Renders the login page
    def get(self):
        session    = get_current_session()
        session.regenerate_id()
        user_email = session.get('email', '');
        url        = self.request.get( 'u' )
        client     = self.get_client()
        
        logging.info("URL : %s EMAIL: %s" % (url, user_email) )
        
        if len(user_email) > 0 and client:
            previousAuthErrors = session.get('auth-errors', False)
            previousRegErrors  = session.get('reg-errors', False)
            
            # we authenticated so clear error cache
            if previousAuthErrors or previousRegErrors:
                session['auth-errors'] = []
                session['reg-errors']  = [] 
                
            self.redirect( url if url else '/account' )
        
        else:
            stats      = Stats.all().get()
            registered = self.request.cookies.get('willt-registered', False)
            clientEmail = session.get('correctEmail', '')
            authErrors = session.get('auth-errors', [])
            regErrors  = session.get('reg-errors', [])
            
            template_values = {  'email': clientEmail,
                                 'authErrors': authErrors,
                                 'regErrors': regErrors,
                                 'loggedIn': False,
                                 'registered': str(registered).lower(),
                                 'url' : url,
                                 'stats' : stats,
                                 'total_users' : stats.total_clients + stats.total_users if stats else 'Unavailable' }
                                 
            self.response.out.write(self.render_page('login.html', template_values))

class ShowDemoSitePage( URIHandler ):
    # Renders the main template
    def get(self, page):
        template_values = {
            'LANDING_CAMPAIGN_UUID' : LANDING_CAMPAIGN_UUID        
        }
        
        if page == '' or page == '/':
            page = 'thanks'
        
        self.response.out.write(self.render_page('demo_site/%s.html' % page, template_values))

##-----------------------------------------------------------------------------##
##------------------------- The Shows -----------------------------------------##
##-----------------------------------------------------------------------------##

class ShowAccountPage( URIHandler ):
    # Renders the account page.
    def get(self):
        client  = self.get_client() # may be None
        to_show = []
        
        # Show the Client's campaigns
        if hasattr( client, 'campaigns' ) and client.campaigns.count() > 0:
            has_campaigns = True 
            campaigns     = client.campaigns.order( '-created' )
            
            for c in campaigns:
                to_show.append({'title'    : c.title,
                                'uuid'     : c.uuid,
                                'target_url' : c.target_url,
                                'date'     : c.created.strftime('%A %B %d, %Y'),
                                'shares'   : c.get_shares_count(),
                                'clicks'   : c.count_clicks(),
                                'is_shopify' : c.shopify_token != ''})
        else:
            has_campaigns = False
        
        template_values = { 'campaigns' : to_show,
                            'has_campaigns' : has_campaigns }
        
        self.response.out.write(self.render_page('account.html', template_values))

class ShowUserJSON (URIHandler):
    def get(self, user_id = None):
        user = get_user_by_uuid(user_id)
        response = {}
        success = False
        if user:
            #response['user'] = user
            d = {
                'uuid': user.uuid,
                'handle': user.get_handle(),
                'name': user.get_full_name(),
                'pic': user.get_attr('pic'),
                'kscore': user.get_attr('kscore'),
                'has_twitter': (user.get_attr('twitter_handle') != None),
                'has_facebook': (user.get_attr('fb_name') != None),
                'has_linkedin': (user.get_attr('linkedin_first_name') != None),
                'has_email': (user.get_attr('email') != ''),
                'reach': user.get_reach(),
                'created': str(user.get_attr('creation_time').date())
            }
            response['user'] = d
            success = True
        response['success'] = success
        self.response.out.write(json.dumps(response))

class ShowResultsPage( URIHandler ):
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
        
        template_values['api_key'] = MIXPANEL_API_KEY
        template_values['platform_secret'] = hashlib.md5(MIXPANEL_SECRET + campaign.uuid).hexdigest()
        template_values['totals'] = totals
        template_values['service_totals'] = service_totals
        template_values['BASE_URL'] = URL
        logging.info(service_totals) 
        self.response.out.write(self.render_page('dashboard/index.html', template_values))

class ShowResultsJSONPage( URIHandler ):
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

##-----------------------------------------------------------------------------##
##------------------------- The Dos -------------------------------------------##
##-----------------------------------------------------------------------------##

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

class DoAddFeedback( URIHandler ):
    def post( self ):
        client = self.get_client()
        msg    = self.request.get('message')
        
        feedback = Feedback( client=client, message=msg )
        feedback.put()
        
        self.redirect( '/about?thx=1' )

class DoAuthenticate( URIHandler ):
    def post( self ):
        url        = self.request.get( 'url' )
        clientEmail  = cgi.escape(self.request.get("email"))
        passphrase = cgi.escape(self.request.get("passphrase"))
        errors = [ ] # potential login errors
        
        # initialize session
        session = get_current_session()
        session.regenerate_id()
        
        if session.is_active(): # close any active sessions since the user is logging in
            session.terminate()
        
        # set visited cookie so 'register' tab does not appear again
        set_visited_cookie(self.response.headers) 
                
        # user authentication
        code, client, errStr = authenticate(clientEmail, passphrase)
        
        if code != 'OK': # authentication failed
            errors.append(errStr) 
            session['correctEmail'] = clientEmail
            session['auth-errors'] = errors
            self.response.out.write("/login?u=%s" % url)
            return
        
        # authentication successful
        session['email'] = clientEmail
        session['auth-errors'] = [ ]
        
        # Cache the client!
        self.db_client = client
        
        # Link Client -> User if we have a User cookie
        if hasattr( client, 'client_user' ) and client.client_user.count() == 0: 
            user = get_user_by_cookie( self )
            if user:
                logging.info('Attaching Client %s (%s) to User %s (%s)' % (client.uuid, client.email, user.uuid, user.get_attr('email')))
                user.client = client
                user.put()
        
        self.response.out.write( url if url else '/account' )
        return
    

class DoRegisterClient( URIHandler ):
    def post( self ):
        url         = self.request.get( 'url' )
        clientEmail = cgi.escape(self.request.get("email"))
        passwords   = [cgi.escape(self.request.get("passphrase")),
                       cgi.escape(self.request.get("passphrase2"))]
        errors      = []
        
        # initialize session
        session = get_current_session()
        session.regenerate_id()
        
        # remember form values
        session['correctEmail'] = clientEmail
        
        # attempt to register the user
        status, client, errMsg = register(clientEmail, passwords[0], passwords[1])
        
        if status == 'EMAIL_TAKEN': # username taken
            errors.append(errMsg)
            session['reg-errors'] = errors
            # set 'visited' cookie since this is a known address
            set_visited_cookie(self.response.headers) 
            self.response.out.write("/login?u=%s" % url)
            return
        elif status == "UNMATCHING_PASS":
            errors.append(errMsg)
            session['reg-errors'] = errors
            session['auth-errors'] = []
            self.response.out.write("/login?u=%s" % url)
            return
        else:
            # set visited cookie so 'register' tab does not appear again
            set_visited_cookie(self.response.headers) 
            session['email']      = client.email
            session['reg-errors'] = [ ]
            
            # Cache the client!
            self.db_client = client
            
            # Link Client -> User if we have a User cookie
            if hasattr( client, 'client_user' ) and client.client_user.count() == 0: 
                user = get_user_by_cookie( self )
                if user:
                    logging.info('Attaching Client %s (%s) to User %s (%s)' % (client.uuid, client.email, user.uuid, user.get_attr('email')))
                    user.client = client
                    user.put()
            
            self.response.out.write( url if url else '/account' )
            return

class Logout( URIHandler ):
    def get( self ):
        session = get_current_session()
        session.regenerate_id()
        
        if session.is_active():
            session.terminate()
        
        self.db_client = None # Remove this client
        
        self.redirect( '/' )

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

##-----------------------------------------------------------------------------##
##------------------------- The URI Router ------------------------------------##
##-----------------------------------------------------------------------------##
def main():
    application = webapp.WSGIApplication([
        (r'/about', ShowAboutPage),
        (r'/account', ShowAccountPage),
        (r'/campaign/get_user/(.*)/', ShowUserJSON),
        (r'/campaign/(.*)/', ShowResultsPage),
        (r'/code', ShowCodePage),
        (r'/contact', ShowAboutPage),
        (r'/edit', ShowEditPage),
        (r'/login', ShowLoginPage),
        (r'/demo(.*)',ShowDemoSitePage),

        # json services
        (r'/campaign.json', ShowResultsJSONPage),
        
        (r'/auth', DoAuthenticate),
        (r'/doFeedback', DoAddFeedback),
        (r'/deleteCampaign', DoDeleteCampaign),
        (r'/doUpdateOrCreateCampaign', DoUpdateOrCreateCampaign),
        (r'/logout', Logout),
        (r'/register', DoRegisterClient),

        (r'/()', ShowLandingPage)
        
        ], debug=USING_DEV_SERVER)
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
