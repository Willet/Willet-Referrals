# TODO: Do these need to be models, or can we leave them as a service?
import logging
from urllib import urlencode
from google.appengine.api.urlfetch import fetch, InvalidURLError
from util.consts import SHOPIFY_APPS
from django.utils import simplejson as json

class SocialNetwork():
    _response_types = ["text/plain", "text/javascript", "application/json"]
    _response_codes = [200, 201]

    @classmethod
    def post(cls, post, **kwargs):
        pass #raise NotImplementedError("Class must implement 'post' method!")

    @classmethod
    def _request(cls, url, verb="GET", payload=None, headers=None):
        """ Returns a the result of a request.

        Returns the following:
        - success: If the request succeeded or not
        - result : The result or a reason for failure
        """
        if payload:
            payload = urlencode(payload)

        if not headers:
            headers = {}

        try:
            response = fetch(url, payload=payload, method=verb, headers=headers)
        except InvalidURLError:
            return False, "Problem making request. Invalid URL"
        except:
            return False, "Problem making request. Not sure why..."

        if not any(x in response.headers["content-type"] for x in cls._response_types):
            return False, "Invalid content type: %s" % response.headers["content-type"]

        if not int(response.status_code) in cls._response_codes:
            return False, "Invalid status code: %s" % response.status_code

        # Other checks?

        return True, response.content

    @classmethod
    def _render_message(cls, message):
        return message


class Facebook(SocialNetwork):
    __graph_url        = "https://graph.facebook.com/"
    __fql_url          = __graph_url + "fql"
    __destination_url  = __graph_url + "feed"
    __access_token_url = __graph_url + "oauth/access_token"

    @classmethod
    def post(cls, post, **kwargs):
        """Posts to Facebook.

        Returns whether or not the post was successful."""
        if not kwargs.get("product"):
            return False

        product = kwargs.get("product")
        logging.info("Product: %s" % product)

        url     = product.resource_url  # Assume this is a canonical URL
        page_id = cls._get_page_id(url)
        logging.info("Page Id: %s" % page_id)

        token   = cls._get_access_token()
        logging.info("Token: %s" % token)

        message = cls._render_message(post.content)
        logging.info("Message: %s" % message)

        success, content = cls._request(cls.__destination_url, "POST", {
            "id"          : page_id,
            "message"     : message,
            "access_token": token
        })

        if not success:
            logging.error("FB Post Error: %s" % content)

        return success

    @classmethod
    def get_reach(cls, url):
        query = "SELECT url, normalized_url, share_count, like_count, "\
                "comment_count, total_count, commentsbox_count, "\
                "comments_fbid, click_count "\
                "FROM link_stat "\
                "WHERE url='%s'" % url
        final_url = "%s?%s" % (cls.__fql_url, query)
        success, content = cls._request(final_url)

        reach = {}

        if success:
            data = content.get("data")
            if data:
                reach = data[0]
        else:
            logging.error("FB Page Error: %s", content)

        return reach

    @classmethod
    def _get_access_token(cls):
        success, content = cls._request(cls.__access_token_url, "POST", {
            "grant_type"   : "client_credentials",
            "redirect_uri" : cls.__access_token_url,
            "client_id"    : SHOPIFY_APPS["ReEngageShopify"]["facebook"]["app_id"],
            "client_secret": SHOPIFY_APPS["ReEngageShopify"]["facebook"]["app_secret"]
        })

        token = None
        if success:
            token = content.split("=")[1]
        else:
            logging.error("FB Token Error: %s" % content)

        return token

    @classmethod
    def _get_page_id(cls, url):
        data      = { "id": url }
        final_url = "%s?%s" % (cls.__graph_url, urlencode(data))

        success, content = cls._request(final_url, payload=data)

        id = None
        if success:
            try:
                result_dict = json.loads(content)
                id = result_dict.get("id")
            except:
                logging.error("FB Page Error: %s" % content)
                id = None
        else:
            logging.error("FB Page Error: %s" % content)

        return id