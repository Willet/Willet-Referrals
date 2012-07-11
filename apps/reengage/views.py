from apps.client.shopify.models import ClientShopify
from util.consts import SHOPIFY_APPS
from util.gaesessions import get_current_session, Session
from util.urihandler import URIHandler
from util.helpers import   url as build_url
from apps.reengage.models import *

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

        session = get_current_session()
        qs_params = {
            "t"   : app.store_token,
            "shop": app.store_url,
        }

        if created:
            page = build_url("ReEngageInstructions", qs=qs_params)
        elif session.is_active():
            page = build_url("ReEngageQueueHandler", qs=qs_params)
        else:
            page = build_url("ReEngageLogin", qs=qs_params)

        self.redirect(page)

class ReEngageInstructions(URIHandler):
    """Display the instructions page."""
    def get(self):
        self.response.out.write(self.render_page('instructions.html', {}))

class ReEngageLogin(URIHandler):
    def get(self):
        """Display the login page"""
        token  = self.request.get( 't' )
        shop   = self.request.get("shop")
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
        token    = self.request.get("t")
        shop     = self.request.get("shop")

        username = self.request.get("username")
        password = self.request.get("password")

        if username == "username" and password == "password":
            session = get_current_session()
            session.regenerate_id()

            session['t']    = token
            session['shop'] = shop

            page = build_url("ReEngageQueueHandler", qs={})
        else:
            page = build_url("ReEngageLogin", qs={
                "t": token,
                "shop" : shop
            })

        self.redirect(page)

class ReEngageLogout(URIHandler):
    def get(self):
        # Redirect to previous URL
        pass

    def post(self):
        """Display the 'logged out' page"""
        session = get_current_session()
        session.terminate()
        pass