#!/usr/bin/env python
import cgi

from apps.client.models import Client, authenticate 
from apps.stats.models  import Stats
from apps.user.models   import get_user_by_cookie

from util.urihandler    import URIHandler
from util.consts        import *
from util.gaesessions   import *
from util.helpers       import *

class ShowAccountPage( URIHandler ):
    # Renders the account page.
    def get(self):
        client  = self.get_client() # may be None
        to_show = []
        has_apps = False
        num_apps = 0

        # Show the Client's apps
        if client == None:
            pass
        elif hasattr(client, 'apps') and client.apps.count() > 0:
            has_apps = True 
            apps     = client.apps.order( '-created' )
            num_apps = client.apps.count()

            for c in apps:
                to_show.append({'title'    : c.product_name,
                                'uuid'     : c.uuid,
                                'target_url' : c.target_url,
                                'date'     : c.created.strftime('%A %B %d, %Y'),
                                'shares'   : c.get_shares_count(),
                                'clicks'   : c.count_clicks(),
                                'is_shopify' : hasattr(c, 'shopify_token')})
        
        template_values = {
            'apps' : to_show,
            'has_apps' : has_apps,
            'current': 'dashboard',
            'BASE_URL': URL,
            'api_key': MIXPANEL_API_KEY,
            'platform_secret': hashlib.md5(MIXPANEL_SECRET + '1234').hexdigest(),
            'num_apps': num_apps
        }
        
        self.response.out.write(self.render_page('account.html', template_values))

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
            session['auth-errors']  = errors
            self.response.out.write("/login?u=%s" % url)
            return
        
        # authentication successful
        session['email']       = clientEmail
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
        
        self.response.out.write( url if url else '/client/account' )
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
                
            self.redirect( url if url else '/client/account' )
            return
        
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

class Logout( URIHandler ):
    def get( self ):
        session = get_current_session()
        session.regenerate_id()
        
        if session.is_active():
            session.terminate()
        
        self.db_client = None # Remove this client
        
        self.redirect( '/' )
