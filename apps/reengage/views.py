from apps.client.models import Client
from apps.client.shopify.models import ClientShopify
from util.consts import SHOPIFY_APPS
from util.gaesessions import get_current_session, Session
from util.urihandler import URIHandler
from util.helpers import   url as build_url
from apps.reengage.models import *

# TODO: Consider moving some of this to a Context Processor

class ReEngageButtons(URIHandler):
    """Handles iframe requests (or otherwise) for ReEngage buttons

    Facebook like buttons don't need to be on the domain that they like, but
    in order for apps to access a like button, they do need to be on the
    same domain. So, we do shenanigans by embedding the button on a page we
    own.

    Required Params
    url        : Canonical URL for the product
    image      : Image that represents the product
    site       : Name of the site hosting the product
    title      : Title of the product
    description: Description of the product

    Optional Params
    app_id     : The Facebook app_id to use with the like button: Defaults to '340019906075293'
    type       : An OpenGraph type. Defaults to 'product'
    """
    def get(self):
        required_params = ["url", "image", "site", "title", "description"]

        if not all(x in self.request.GET for x in required_params):
            logging.error("Missing one of the following GET params: %s"
                % required_params)
            self.error(400)
        else:
            self.response.out.write(self.render_page('buttons.html', {
                "request": self.request.GET
            }))

class ReEngageAppPage(URIHandler):
    """Display the default 'welcome' page."""
    def get(self):
        template_values = {
            "SHOPIFY_API_KEY": SHOPIFY_APPS['ReEngageShopify']['api_key']
        }

        self.response.out.write(self.render_page('beta.html',
                                                 template_values))


class ReEngageShopifyWelcome(URIHandler):
    """Acts as a router for requests from shopify"""
    def get(self):
        token  = self.request.get( 't' )
        shop   = self.request.get("shop")
        client = ClientShopify.get_by_url(shop)
        logging.debug('[RE] %s.%s: %r' % (self.__class__.__name__, 'get', [client, token, shop]), exc_info=True)

        # Fetch or create the app
        app, created = ReEngageShopify.get_or_create(client,token=token)

        if not app:
            pass  # TODO: Error

        session         = get_current_session()
        session["t"]    = token
        session["shop"] = shop

        if created:
            logging.info("Recently created, loading instructions...")
            page = build_url("ReEngageInstructions", qs={})
        elif session.is_active() and session.get('logged_in'):
            logging.info("Session is active, going to main page...")
            page = build_url("ReEngageQueueHandler", qs={})
        else:
            logging.info("No active session, going to login page...")
            page = build_url("ReEngageLogin", qs={})

        self.redirect(page)


class ReEngageInstructions(URIHandler):
    """Display the instructions page."""
    def get(self):
        session = get_current_session()

        shop_url = session.get("shop")

        shop_owner = "Savvy shopper"
        shop_name  = "Your Shop"
        if shop_url:
            try:
                client = ClientShopify.get_by_url(shop_url)
                shop_owner = client.merchant.get_full_name()
                shop_name  = client.name
            except Exception:
                # Client has no merchant
                logging.error("Client %r has no merchant.  Using fake values" % (client,))

        login_url = build_url("ReEngageLogin")

        self.response.out.write(self.render_page('instructions.html', {
            'shop_owner': shop_owner,
            'shop_name' : shop_name,
            'login_url' : login_url,
            'store_url' : shop_url or "mystore.shopify.com"
        }))


class ReEngageHowTo(URIHandler):
    """Display the instructions page."""
    def get(self):
        self.response.out.write(self.render_page('howto.html', {}))


class ReEngageLogin(URIHandler):
    def get(self):
        """Display the login page"""
        session = get_current_session()
        token  = session.get( 't' )
        shop   = session.get("shop")
        logging.debug('[RE] %s.%s: %r' % (self.__class__.__name__, 'get', [session, token, shop]), exc_info=True)
        client = ClientShopify.get_by_url(shop)

        # Fetch or create the app
        app, created = ReEngageShopify.get_or_create(client, token=token)

        if not app:
            pass  # TODO: error

        # TODO: if session is already active

        self.response.out.write(self.render_page('login.html', {
            "host" : self.request.host_url,
        }))

    def post(self):
        """User has submitted their credentials"""
        session  = get_current_session()
        token    = session.get("t")
        shop     = session.get("shop")

        username = self.request.get("username")
        password = self.request.get("password")

        user = ReEngageAccount.all().filter(" email = ", username).get()
        logging.info("User: %s" % user)

        if user and user.verify(password):
            session = get_current_session()
            session.regenerate_id()

            session['logged_in'] = True
            session['t']         = token
            session['shop']      = shop

            self.redirect(build_url("ReEngageQueueHandler", qs={}))
        else:
            self.response.out.write(self.render_page('login.html', {
                "host" : self.request.host_url,
                "msg": "Username or password incorrect",
                "cls": "error",
            }))



class ReEngageLogout(URIHandler):
    def get(self):
        self.post()

    def post(self):
        """Display the 'logged out' page"""
        session = get_current_session()
        token   = session.get("t")
        shop    = session.get("shop")

        page    = build_url("ReEngageLogin", qs={})

        session.terminate()

        session["t"]    = token
        session["shop"] = shop

        self.redirect(page)


class ReEngageCreateAccount(URIHandler):
    def get(self):
        """Show the 'create an account' page"""
        self.response.out.write(self.render_page('login.html', {
            "host" : self.request.host_url,
        }))

    def post(self):
        """Take the users account details and create an account"""
        username = self.request.get("username")

        user, created = ReEngageAccount.get_or_create(username)

        if user and created:  # Activate account
            logging.info("User was created")
            self.response.out.write(self.render_page('login.html', {
                "msg": "You have been sent an email with further instructions.",
                "cls": "success",
                "host" : self.request.host_url
            }))
        elif user:  # Account already exists
            logging.info("User already exists")
            self.response.out.write(self.render_page('login.html', {
                "username": username,
                "msg": "Sorry, that email is already in use.",
                "host" : self.request.host_url,
                "cls": "error",
            }))
            pass
        else:  # Some mistake
            self.response.out.write(self.render_page('login.html', {
                "username": username,
                "msg": "There was a problem creating your account.<br/>Please"
                       " try again later",
                "host" : self.request.host_url,
                "cls": "error",
            }))


class ReEngageResetAccount(URIHandler):
    def get(self):
        """Show the user the 'reset' form"""
        self.response.out.write(self.render_page('reset.html', {
            "host" : self.request.host_url,
            "show_form": True
        }))

    def post(self):
        """Take the user's details and reset their account"""
        email = self.request.get("username")

        user = ReEngageAccount.all().filter(" email = ", email).get()

        if not user:
            context = {
                "msg": "No user found :("
            }
        else:
            user.forgot_password()
            context = {
                "msg": "An email has been sent to your account with details "
                       "to reset your password."
            }

        self.response.out.write(self.render_page('reset.html', context))


class ReEngageVerify(URIHandler):
    def get(self):
        """Verify that the token provided was correct"""
        session = get_current_session()

        email = self.request.get("email") or session.get("email")
        token = self.request.get("token") or session.get("token")

        session["email"] = email
        session["token"] = token

        user = ReEngageAccount.all().filter(" email = ", email).get()

        if not user:
            # Nothing to verify
            context = {
                "msg": "No user found :(",
                "cls": "error"
            }
        elif user.token != token:
            # Token is invalid
            context = {
                "msg": "Tokens do not match. Please try the link from the "
                       "email again.",
                "cls": "error"
            }
        elif user.token_exp < datetime.datetime.now():
            # Token has expired. Send a new token?
            context = {
                "msg": "Your token has expired. You should be "
                       "receiving a new one in an email shortly :)",
                "cls": "error"
            }
            user.forgot_password()
        else:
            # All is well
            context = {
                "set_password": True
            }

        self.response.out.write(self.render_page('verify.html', context))

    def post(self):
        """Set the user's new password"""
        session = get_current_session()

        email    = session.get("email")
        token    = session.get("token")

        password = self.request.get("password")
        verify   = self.request.get("password2")

        user = ReEngageAccount.all().filter(" email = ", email).get()

        if password and verify and password != verify:
            context = {
                "msg": "Passwords don't match.",
                "cls": "error"
            }
        elif not (user and user.token == token):
            context = {
                "msg": "There was a problem verifying your account.",
                "cls": "error"
            }
        else:
            user.token     = None
            user.token_exp = None
            user.verified  = True
            user.set_password(password)

            user.put()

            url = build_url("ReEngageLogin")
            context = {
                "msg": "Successfully set password. "
                       "Please <a href='%s'>log in</a>." % url,
                "cls": "success"
            }

        self.response.out.write(self.render_page('verify.html', context))


class ReEngageCPLServeScript(URIHandler):
    """Serve the reengage script with some template variables."""
    def get(self):
        """Required variable: client_uuid."""
        session = get_current_session()
        client = Client.get_by_url(session.get('shop'))
        if not client:
            logging.warn('client not found; exiting')
            self.error(400)
            return

        template_values = {
            'client': client,
        }

        self.response.headers.add_header('content-type', 'text/javascript', charset='utf-8')
        self.response.out.write(self.render_page('js/com.js', template_values))
