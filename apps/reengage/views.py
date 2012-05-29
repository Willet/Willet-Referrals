import logging
from urllib import urlencode
from util import httplib2
from util.urihandler import URIHandler
from util.local_consts import SHOPIFY_APPS
from django.utils import simplejson as json
from util.helpers import url as build_url

class ReEngageFacebook(URIHandler):
    def get(self):
        template_values = {}
        self.response.out.write(self.render_page('fb.html', template_values))

    def post(self):
        url     = self.request.get("url")
        message = self.request.get("message", "Remember me?")

        # get an access token
        token = self._FB_get_access_token()

        # get the id of the page
        page_id = self._FB_get_page_id(url)

        # post the message
        self._FB_post(message, page_id, token)

        self.redirect(build_url("ReEngageFacebook"))

    def _FB_get_access_token(self):
        access_token_url = "https://graph.facebook.com/oauth/access_token"
        data = {
            "grant_type"   : "client_credentials",
            "redirect_uri" : access_token_url,
            "client_id"    : SHOPIFY_APPS["ReEngage"]["facebook"]["app_id"],
            "client_secret": SHOPIFY_APPS["ReEngage"]["facebook"]["app_secret"]
        }

        http = httplib2.Http()
        response, content = http.request(access_token_url,
                                         "POST",
                                         urlencode(data))
        logging.info("Response: %s" % response)
        logging.info("Content : %s" % content)

        token = content.split("=")[1]
        return token

    def _FB_get_page_id(self, url):
        graph_url = "https://graph.facebook.com/"
        data = {
            "id": url
        }
        final_url = "%s?%s" % (graph_url, urlencode(data))
        logging.info(final_url)

        http = httplib2.Http()
        response, content = http.request(final_url, "GET")

        logging.info("Response: %s" % response)
        logging.info("Content : %s" % content)

        result_dict = json.loads(content)
        return result_dict["id"]

    def _FB_post(self, message, page_id, token):
        destination_url = "https://graph.facebook.com/feed"
        data = {
            "id"          : page_id,
            "message"     : message,
            "access_token": token
        }

        http = httplib2.Http()
        response, content = http.request(destination_url,
                                         "POST",
                                         urlencode(data))

        logging.info("Response: %s" % response)
        logging.info("Content : %s" % content)

