from apps.client.shopify.models import ClientShopify
from util.consts import SHOPIFY_APPS
from util.gaesessions import get_current_session, Session
from util.urihandler import URIHandler
from util.helpers import   url as build_url
from apps.reengage.models import *

# TODO: Consider moving some of this to a Context Processor

class ReEngageAppPage(URIHandler):
    """Display the default 'welcome' page."""
    def get(self):
        template_values = {
            "SHOPIFY_API_KEY": SHOPIFY_APPS['ReEngageShopify']['api_key']
        }

        self.response.out.write(self.render_page('app_page.html',
                                                 template_values))


class ReEngageLanding(URIHandler):
    def get(self):
        token  = self.request.get( 't' )
        shop   = self.request.get("shop")
        client = ClientShopify.get_by_url(shop)

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
        self.response.out.write(self.render_page('instructions.html', {}))

class ReEngageLogin(URIHandler):
    def get(self):
        """Display the login page"""
        session = get_current_session()
        token  = session.get( 't' )
        shop   = session.get("shop")
        client = ClientShopify.get_by_url(shop)

        # Fetch or create the app
        app, created = ReEngageShopify.get_or_create(client, token=token)

        if not app:
            pass  # TODO: error

        # TODO: if session is already active

        self.response.out.write(self.render_page('login.html', {
            "host" : self.request.host_url,
            "t": token,
            "shop" : shop
        }))

    def post(self):
        session  = get_current_session()
        token    = session.get("t")
        shop     = session.get("shop")

        username = self.request.get("username")
        password = self.request.get("password")

        if username == "username" and password == "password":
            session = get_current_session()
            session.regenerate_id()

            session['logged_in'] = True
            session['t']         = token
            session['shop']      = shop

            page = build_url("ReEngageQueueHandler", qs={})
        else:
            page = build_url("ReEngageLogin", qs={
                "t": token,
                "shop" : shop
            })

        self.redirect(page)

class ReEngageLogout(URIHandler):
    def get(self):
        # TODO: Redirect to previous URL
        pass

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
        pass

    def post(self):
        pass

class ReEngageResetAccount(URIHandler):
    def get(self):
        pass

    def post(self):
        pass