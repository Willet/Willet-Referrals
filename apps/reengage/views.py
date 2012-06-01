import logging
from urllib import urlencode
from util import httplib2
from util.urihandler import URIHandler
from util.local_consts import SHOPIFY_APPS
from django.utils import simplejson as json
from util.helpers import url as build_url

def _FB_request(url, verb="GET", payload=None):
    """ Returns a the result of a request.

    Returns the following:
    - success: If the request succeeded or not
    - result : The result or a reason for failure
    """
    response_types = ["text/plain", "text/javascript", "application/json"]
    status_codes   = [200, 201]
    response       = None
    content        = None

    http = httplib2.Http()
    try:
        if payload:
            response, content = http.request(url, verb, urlencode(payload))
        else:
            response, content = http.request(url, verb)
    except:
        return False, "Problem making request. Invalid URL / Verb?"

    if not any(x in response["content-type"] for x in response_types):
        return False, "Invalid content type"

    if not int(response.status) in status_codes:
        return False, "Invalid status code"

    # Other checks?

    logging.info("Response: %s" % response)
    logging.info("Content : %s" % content)

    return True, content

def _FB_get_access_token():
    access_token_url = "https://graph.facebook.com/oauth/access_token"
    data = {
        "grant_type"   : "client_credentials",
        "redirect_uri" : access_token_url,
        "client_id"    : SHOPIFY_APPS["ReEngage"]["facebook"]["app_id"],
        "client_secret": SHOPIFY_APPS["ReEngage"]["facebook"]["app_secret"]
    }

    success, content = _FB_request(access_token_url, "POST", data)

    token = None
    if success:
        token = content.split("=")[1]
    else:
        logging.error("FB Token Error: %s" % content)

    return token

def _FB_get_page_id(url):
    graph_url = "https://graph.facebook.com/"
    data = {
        "id": url
    }
    final_url = "%s?%s" % (graph_url, urlencode(data))

    success, content = _FB_request(final_url, payload=data)

    id = None
    if success:
        try:
            result_dict = json.loads(content)
            id = result_dict["id"]
        except:
            logging.error("FB Page Error: %s" % content)
            return None
    else:
        logging.error("FB Page Error: %s" % content)

    return id

def _FB_post(message, page_id, token):
    destination_url = "https://graph.facebook.com/feed"
    data = {
        "id"          : page_id,
        "message"     : message,
        "access_token": token
    }

    success, content = _FB_request(destination_url, "POST", data)

    if not success:
        logging.error("FB Post Error: %s" % content)

    return success

class ReEngageControlPanel(URIHandler):
    def get(self):
        self.response.out.write(self.render_page('control_panel.html', {}))

class ReEngageProduct(URIHandler):
    def get(self):
        self.response.out.write(self.render_page('product.html', {
            "DOMAIN": self.request.host_url
        }))

class ReEngageFacebook(URIHandler):
    def get(self):
        message = self.request.get("message", "")
        template_values = {
            "message": message,
            "DOMAIN": self.request.host_url
        }
        self.response.out.write(self.render_page('fb.html', template_values))

    def post(self):
        url     = self.request.get("url")
        message = self.request.get("message", "Remember me?")

        # get an access token
        token = _FB_get_access_token()

        if not token:
            message = {
                "message": "Your application seems to be misconfigured."
            }
            self.redirect(build_url("ReEngageControlPanel", qs=message))
            return

        # get the id of the page
        page_id = _FB_get_page_id(url)

        if not page_id:
            message = {
                "message": "We couldn't message the page you requested."
            }
            self.redirect(build_url("ReEngageControlPanel", qs=message))
            return

        # post the message
        success = _FB_post(message, page_id, token)

        if not success:
            message = {
                "message": "There was a problem posting the message."
            }
            self.redirect(build_url("ReEngageControlPanel", qs=message))
            return

        message = {
            "message": "Message sent successfully!"
        }
        self.redirect(build_url("ReEngageControlPanel", qs=message))






