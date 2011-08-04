#!/usr/bin/python

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc."

import hashlib, re

from django.utils import simplejson as json
from gaesessions import get_current_session
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api.datastore_errors import BadValueError

from models.client   import Client, get_client_by_email, authenticate, register
from models.campaign import get_campaign_by_id, Campaign
from models.feedback import Feedback
from models.stats    import Stats
from models.user     import User
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

        logging.info("URL : %s" % url )

        if len(user_email) > 0:
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
            userEmail  = session.get('correctEmail', '')
            authErrors = session.get('auth-errors', [])
            regErrors  = session.get('reg-errors', [])
            
            template_values = {  'email': userEmail,
                                 'authErrors': authErrors,
                                 'regErrors': regErrors,
                                 'loggedIn': False,
                                 'registered': str(registered).lower(),
                                 'url' : url,
                                 'stats' : stats,
                                 'total_users' : stats.total_clients + stats.total_users if stats else 'Unavailable' }

            self.response.out.write(self.render_page('login.html', template_values))

class ShowDemoPage( URIHandler ):
    # Renders the main template
    def get(self):
        template_values = { }
        
        self.response.out.write(self.render_page('demo.html', template_values))

##-----------------------------------------------------------------------------##
##------------------------- The Shows -----------------------------------------##
##-----------------------------------------------------------------------------##

class ShowButton( URIHandler ):
    # Renders the main template
    def get(self):
        template_values = {}
        campaign_id     = self.request.get('ca_id')
        user_id         = self.request.get('uid')

        campaign = get_campaign_by_id( campaign_id )
        if campaign == None:
            campaign = get_campaign_by_id( LANDING_CAMPAIGN_UUID )
        
        template_values = { 'campaign_id' : campaign_id,
                            'button_text' : campaign.button_text,
                            'button_subtext' : campaign.button_subtext,
                            'uid' : user_id }
    
        self.response.out.write(self.render_page('button.html', template_values))

class ShowTweetButton( URIHandler ):
    def get(self):
        template_values = {}
        campaign_id     = self.request.get('ca_id')
        user_id         = self.request.get('uid')

        campaign = get_campaign_by_id( campaign_id )
        if campaign == None:
            template_values['error'] = True
        else:
            template_values = { 'campaign_id' : campaign_id, 'uid' : user_id }
        
        self.response.out.write(self.render_page('tweet_button.html', template_values))


class ShowAccountPage( URIHandler ):
    # Renders the account page.
    def get(self):
        client  = self.get_client() # may be None
        to_show = []

        # Show the Clients campaigns
        if hasattr( client, 'campaigns' ) and client.campaigns.count() > 0:
            has_campaigns = True 
            campaigns     = client.campaigns.order( '-created' )
            
            for c in campaigns:
                to_show.append({'title'    : c.title,
                                'uuid'     : c.uuid,
                                'target_url' : c.target_url,
                                'date'     : c.created.strftime('%A %B %d, %Y'),
                                'shares'   : c.get_shares_count(),
                                'clicks'   : c.count_clicks()})
        else:
            has_campaigns = False
        
        template_values = { 'campaigns' : to_show,
                            'has_campaigns' : has_campaigns }
        
        self.response.out.write(self.render_page('account.html', template_values))


class ShowViewCampaignPage( URIHandler ):
    # Renders a campaign page
    def get(self):
        client          = self.get_client()
        campaign_id     = self.request.get( 'id' )
        template_values = { 'campaign' : None }

        if campaign_id:
            
            # Grab the campaign
            campaign = get_campaign_by_id( campaign_id )
            if campaign == None:
                self.redirect( '/account' )
                return

            template_values['campaign'] = campaign
            
            total_clicks = campaign.count_clicks()
            template_values['total_clicks'] = total_clicks
            results, mixpanel = campaign.get_results( total_clicks )

            template_values['results']     = results
            template_values['mixpanel']    = mixpanel
            template_values['has_results'] = len( results ) != 0

            template_values['api_key'] = MIXPANEL_API_KEY
            template_values['platform_secret'] = hashlib.md5(MIXPANEL_SECRET + campaign.uuid).hexdigest()

        template_values['BASE_URL'] = URL

        self.response.out.write(self.render_page('view_campaign.html', template_values))

class ShowViewCampaignJSONPage( URIHandler ):
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
            template_values['campaign'] = {'title' : campaign.title, 
                                           'button_text' : campaign.button_text,
                                           'share_text': campaign.share_text, 
                                           'target_url' : campaign.target_url}
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

class ShowEditCampaignPage( URIHandler ):
    # Renders a campaign page
    def get(self):
        client      = self.get_client() # may be None

        campaign_id = self.request.get( 'id' )
        error       = self.request.get( 'error' )
        error_msg   = self.request.get('error_msg')
        title       = self.request.get( 'title' )
        button_text = self.request.get( 'button_text' )
        button_subtext = self.request.get( 'button_subtext' )
        share_text  = self.request.get( 'share_text' )
        target_url  = self.request.get( 'target_url' )
        redirect_url = self.request.get( 'redirect_url' ) # optionally redirect popup after tweet
        webhook_url = self.request.get( 'webhook_url' ) 

        template_values = { 'campaign' : None }

        if client and client.campaigns.count() == 0:
            template_values['show_guiders'] = True

        # Fake a campaign to put data in if there is an error

        if error == '1':
            template_values['show_guiders'] = False
            template_values['error'] = 'Invalid url.'
            template_values['campaign'] = { 'title' : title, 
                                            'button_text' : button_text,
                                            'button_subtext' : button_subtext,
                                            'share_text': share_text, 
                                            'target_url' : target_url,
                                            'webhook_url' : webhook_url,
                                            'redirect_url' : redirect_url }
        elif error == '2':
            template_values['show_guiders'] = False
            template_values['error'] = 'Please don\'t leave anything blank.'
            template_values['campaign'] = { 'title' : title, 
                                            'button_text' : button_text,
                                            'button_subtext' : button_subtext,
                                            'share_text': share_text, 
                                            'target_url' : target_url,
                                            'webhook_url' : webhook_url,
                                            'redirect_url' : redirect_url }
        elif error == '3':
            template_values['show_guiders'] = False
            template_values['error'] = 'There was an error with one of your inputs: %s' % error_msg
            template_values['campaign'] = { 'title' : title, 
                                            'button_text' : button_text,
                                            'button_subtext' : button_subtext,
                                            'share_text': share_text, 
                                            'target_url' : target_url,
                                            'webhook_url' : webhook_url,
                                            'redirect_url' : redirect_url }

        # If there is no campaign_id, then we are creating a new one:
        if campaign_id:
            
            # Updating an existing campaign here:
            campaign = get_campaign_by_id( campaign_id )
            if campaign == None:
                self.redirect( '/account' )
                return
            
            template_values['campaign'] = campaign
            template_values['show_guiders'] = False
        
        template_values['BASE_URL'] = URL
        
        self.response.out.write(self.render_page('edit_campaign.html', template_values))


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
            template_values['show_guiders'] = False
        
        template_values['BASE_URL'] = URL

        self.response.out.write(self.render_page('code.html', template_values))

class ShowTestPage(URIHandler):
    # Renders plugin test page
    def get(self):
        ca_id = self.request.get('ca_id')
        template_values = {'ca_id': ca_id}
        template_values['BASE_URL'] = URL
        self.response.out.write(self.render_page('test.html', template_values))


class ShowTwitterPreviewPage( URIHandler ):
    # Renders the main template
    def get(self):
        template_values = []
        
        self.response.out.write(self.render_page('twitter-preview.html', template_values))


##-----------------------------------------------------------------------------##
##------------------------- The Dos -------------------------------------------##
##-----------------------------------------------------------------------------##

class DoUpdateOrCreateCampaign( URIHandler ):
    def post( self ):
        client = self.get_client() # might be None

        campaign_id     = self.request.get( 'uuid' )
        title           = self.request.get( 'title' )
        button_text     = self.request.get( 'button_text' )
        button_subtext  = self.request.get( 'button_subtext' )
        share_text      = self.request.get( 'share_text' )
        target_url      = self.request.get( 'target_url' )
        redirect_url    = self.request.get( 'redirect_url' )
        webhook_url     = self.request.get( 'webhook_url' )
        
        logging.info(" %s %s %s %s %s %s %s %s" % (campaign_id, share_text, button_text, button_subtext, title, target_url, webhook_url, redirect_url) )
        
        campaign = get_campaign_by_id( campaign_id )
        
        title = title.capitalize() # caps it!
        
        if title == '' or button_text == '' or button_subtext == '' or share_text == '' or target_url == '':
            self.redirect( '/edit?id=%s&error=2&title=%s&button_text=%s&button_subtext=%s&share_text=%s&target_url=%s&redirect_url=%s&webhook_url=%s' % (campaign_id, title, button_text, button_subtext, share_text, target_url, redirect_url, webhook_url) )
            return
            
        if not isGoodURL( target_url ):
            self.redirect( '/edit?id=%s&error=1&title=%s&button_text=%s&button_subtext=%s&share_text=%s&target_url=%s&redirect_url=%s&webhook_url=%s' % (campaign_id, title, button_text, button_subtext, share_text, target_url, redirect_url, webhook_url) )
            return

        # If campaign doesn't exist,
        if campaign == None:
        
            # Create a new one!
            try:
                campaign = Campaign( uuid = generate_uuid(16),
                                     client=client, 
                                     title=title[:100], 
                                     button_text=button_text,
                                     button_subtext=button_subtext,
                                     share_text=share_text[:140],
                                     target_url=target_url,
                                     redirect_url=redirect_url,
                                     webhook_url=webhook_url)
                campaign.put()
            except BadValueError, e:
                self.redirect( '/edit?error=3&error_msg=%s&id=%s&title=%s&button_text=%s&button_subtext=%s&share_text=%s&target_url=%s&webhook_url=%s&redirect_url=%s' % (str(e), campaign_id, title, button_text, button_subtext, share_text, target_url, webhook_url, redirect_url) )
                return
        
        # Otherwise, update the existing campaign.
        else:
            try:
                campaign.update( title=title, 
                             share_text=share_text, 
                             button_text=button_text, 
                             button_subtext=button_subtext,
                             target_url=target_url,
                             redirect_url=redirect_url,
                             webhook_url=webhook_url)
            except BadValueError, e:
                self.redirect( '/edit?error=3&error_msg=%s&id=%s&title=%s&button_text=%s&button_subtext=%s&share_text=%s&target_url=%s&webhook_url=%s&redirect_url=%s' % (str(e), campaign_id, title, button_text, button_subtext, share_text, target_url, webhook_url, redirect_url) )
                return
        
        if client == None:
            self.redirect( '/login?u=/code?id=%s' % campaign.uuid )
        else:
            self.redirect( '/code?id=%s' % campaign.uuid )

 
class TestPage(URIHandler):
    def get(self):
        ca_id = self.request.get('ca_id')
        template_values = {'ca_id': ca_id}
        template_values['BASE_URL'] = URL
        self.response.out.write(self.render_page('test.html', template_values))

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
        userEmail  = cgi.escape(self.request.get("email"))
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
        code, user, errStr = authenticate(userEmail, passphrase)

        if code != 'OK': # authentication failed
            errors.append(errStr) 
            session['correctEmail'] = userEmail
            session['auth-errors'] = errors
            self.response.out.write("/login")
            return

        # authentication successful
        session['email'] = userEmail
        session['auth-errors'] = [ ]
        self.response.out.write( url if url else '/account' )
        return


class DoRegisterClient( URIHandler ):
    def post( self ):
        url       = self.request.get( 'url' )
        userEmail = cgi.escape(self.request.get("email"))
        passwords = [cgi.escape(self.request.get("passphrase")),
                     cgi.escape(self.request.get("passphrase2"))]
        errors = []
        
        # initialize session
        session = get_current_session()
        session.regenerate_id()

        # remember form values
        session['correctEmail'] = userEmail

        # attempt to register the user
        status, user, errMsg = register(userEmail, passwords[0], passwords[1])

        userCheck = Client.all().filter('email =', userEmail).get()
        if status == 'EMAIL_TAKEN': # username taken
            errors.append(errMsg)
            session['reg-errors'] = errors
            # set 'visited' cookie since this is a known address
            set_visited_cookie(self.response.headers) 
            self.response.out.write("/login")
            return
        elif status == "UNMATCHING_PASS":
            errors.append(errMsg)
            session['reg-errors'] = errors
            session['auth-errors'] = []
            self.response.out.write("/login")
            return
        else:
            # set visited cookie so 'register' tab does not appear again
            set_visited_cookie(self.response.headers) 
            session['email']      = user.email
            session['reg-errors'] = [ ]
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
        (r'/button', ShowButton),
        (r'/campaign', ShowViewCampaignPage),
        (r'/campaign.json', ShowViewCampaignJSONPage),
        (r'/code', ShowCodePage),
        (r'/contact', ShowAboutPage),
        (r'/demo', ShowDemoPage),
        (r'/edit', ShowEditCampaignPage),
        (r'/login', ShowLoginPage),
        (r'/test', ShowTestPage),
        (r'/tweet_button', ShowTweetButton),
        (r'/twitterPreview', ShowTwitterPreviewPage),
        
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

