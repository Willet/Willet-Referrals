# TODO: Do these need to be models, or can we leave them as a service?
import logging
import urllib
import urllib2

from urllib import urlencode
from xml.dom import minidom

from google.appengine.api.urlfetch import fetch, InvalidURLError
from util.consts import SHOPIFY_APPS
from django.utils import simplejson as json

class SocialNetwork():
    """A generic class for social networks.

    Social networks are assumed to have a means to post a message (post)"""
    _response_types = ["text/plain", "text/javascript", "application/json"]
    _response_codes = [200, 201]

    @classmethod
    def post(cls, post, **kwargs):
        """Template method for posting to a social network.

        - post: a ReEngagePost object"""
        raise NotImplementedError("Class must implement 'post' method!")

    @classmethod
    def _request(cls, url, verb="GET", payload=None, headers=None):
        """ Returns a the result of a request.

        Returns the following:
        - success: If the request succeeded or not
        - result : The result or a reason for failure
        """
        if payload:
            try:
                payload = urlencode(payload)
            except TypeError:
                return False, "Payload couldn't be URL-encoded"

        if not headers:
            headers = {}

        try:
            response = fetch(url, payload=payload, method=verb, headers=headers)
        except InvalidURLError:
            return False, "Problem making request. Invalid URL"
        except Exception, e:
            return False, "Problem making request. Not sure why: %r" % e

        if not any(x in response.headers["content-type"] for x in cls._response_types):
            return False, "Invalid content type: %s" % response.headers["content-type"]

        if not int(response.status_code) in cls._response_codes:
            return False, "Invalid status code: %s" % response.status_code

        # Other checks?

        return True, response.content

    @classmethod
    def _render_message(cls, message, **kwargs):
        """Replace post tags with their values."""
        # first do product
        product = kwargs.get("product")
        product_tag = '(product)'
        product_name = getattr(product, 'title', False)
        if product and product_name:
            if message.find(product_tag) >= 0:
                logging.info('replacing product tag')
                message = message.replace(product_tag, product_name)
        else:
            logging.warn('product has no title :(')

        # then do collection
        collection = kwargs.get("collection")
        collection_tag = '(category)'  # humans call them categories
        collection_name = getattr(collection, 'collection_name', False)
        if collection and collection_name:
            if message.find(collection_tag) >= 0:
                logging.info('replacing collection tag')
                message = message.replace(collection_tag, collection_name)
        else:
            logging.warn('collection has no name :(')

        logging.info('message became %s' % message)
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
        logging.info("Page url: %s" % url)
        page_id = cls._get_page_id(url)
        logging.info("Page Id: %s" % page_id)

        token   = cls._get_access_token()
        logging.info("Token: %s" % token)

        message = cls._render_message(post.content, product=product)
        logging.info("Message: %s" % message)

        logging.info("Title: %s" % post.title)
        message = cls._render_message(post.content)

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
        """Gets a URL's 'reach' using FQL."""
        def get_node_val(node, key, default=None):
            """helper function(node, 'node'): <node>abc</node> => abc."""
            try:
                return node.getElementsByTagName(key)[0].firstChild.nodeValue
            except:
                return default

        reach = {}
        query = "SELECT url, normalized_url, share_count, like_count, "\
                "comment_count, total_count, commentsbox_count, "\
                "comments_fbid, click_count FROM link_stat WHERE url='%s'" % url
        logging.debug('query = %s' % query)
        params = {'query': query}

        # apparently, only the xml version works
        request_object = urllib2.Request(
            'https://api.facebook.com/method/fql.query',
            urllib.urlencode(params))
        response = urllib2.urlopen(request_object)

        # parse the xml
        contents = response.read()
        pub_node = minidom.parseString(contents).childNodes[0]\
                          .getElementsByTagName('link_stat')[0]

        # get the node values and build a dict to return
        prod_url = get_node_val(pub_node, 'url')
        normalized_url = get_node_val(pub_node, 'normalized_url')
        share_count = get_node_val(pub_node, 'share_count')
        like_count = get_node_val(pub_node, 'like_count')
        comment_count = get_node_val(pub_node, 'comment_count')
        click_count = get_node_val(pub_node, 'click_count')
        total_count = get_node_val(pub_node, 'total_count')
        commentsbox_count = get_node_val(pub_node, 'commentsbox_count')
        comments_fbid = get_node_val(pub_node, 'comments_fbid')

        reach = {'prod_url': prod_url,
                 'normalized_url': normalized_url,
                 'share_count': int(share_count),
                 'like_count': int(like_count),
                 'comment_count': int(comment_count),
                 'click_count': int(click_count),
                 'total_count': int(total_count),
                 'commentsbox_count': int(commentsbox_count),
                 'comments_fbid': comments_fbid}

        logging.debug('reach = %r' % reach)
        return reach

    @classmethod
    def get_reach_count(cls, url):
        """facebok only: use lower-level url call to retrieve a number:
        number of shares of a given product url.

        """
        return cls.get_reach(url).get('total_count', 0)

    @classmethod
    def _get_access_token(cls):
        """Obtains an access token for a FB application."""
        success, content = cls._request(cls.__access_token_url, "POST", {
            "grant_type"   : "client_credentials",
            "redirect_uri" : cls.__access_token_url,
            "client_id"    : SHOPIFY_APPS["ReEngageShopify"]["facebook"]["app_id"],
            "client_secret": SHOPIFY_APPS["ReEngageShopify"]["facebook"]["app_secret"]
        })

        token = None
        if success:
            try:
                token = content.split("=")[1]
            except AttributeError:
                pass
        else:
            logging.error("FB Token Error: %s" % content)

        return token

    @classmethod
    def _get_page_id(cls, url):
        """Obtains the FB opengraph id for a given url"""
        data      = { "id": url }
        final_url = "%s?%s" % (cls.__graph_url, urlencode(data))
        logging.info("Final URL: %s" % final_url)

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