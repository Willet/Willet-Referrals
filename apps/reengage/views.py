import logging
from urllib import urlencode
from google.appengine.api.taskqueue import taskqueue
from apps.reengage.models import TwitterAssociation
from util import httplib2
from util.urihandler import URIHandler
from util.local_consts import SHOPIFY_APPS
from django.utils import simplejson as json
from util.helpers import url as build_url
from util import tweepy

def _ReEngage_request(url, verb="GET", payload=None, headers=None):
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
            response, content = http.request(url, verb, urlencode(payload),
                                             headers)
        else:
            response, content = http.request(url, verb, headers=headers)
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

    success, content = _ReEngage_request(access_token_url, "POST", data)

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

    success, content = _ReEngage_request(final_url, payload=data)

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

    success, content = _ReEngage_request(destination_url, "POST", data)

    if not success:
        logging.error("FB Post Error: %s" % content)

    return success

def _Twitter_find_user_by_query(query):
    """ Search for a twitter user (or users) based on some query.

    Note: It takes somewhere around 30 seconds to go from the intial tweet to
     being searchable with the twitter API
    """
    users    = []

    base_url = "http://search.twitter.com/search.json"
    params   = {
        "q"          : "%s source:tweet_button" % query,
        "result_type": "recent",
        "show_user"  : "true"
    }

    search_url = "%s?%s" %(base_url, urlencode(params))
    logging.info("Search URL: %s" % search_url)

    success, content = _ReEngage_request(search_url)
    logging.info("Success? %s\nContent: %s" % (success, content))

    if not success:
        return users

    results = json.loads(content)

    results = results.get("results")
    if not results:
        return users

    for result in results:
        user = result.get("from_user")
        if user:
            users.append(user)

    return list(set(users))

def _Twitter_associate_user(url, users):
    associations, _ = TwitterAssociation.get_or_create(url)
    for user in users:
        if user not in associations.handles:
            associations.handles.append(user)

    associations.put()

def _Twitter_post(message, url):
    #Oauth is hard: let's go shopping!
    consumer_key    = "xGzwuxKSs1Lc6EFd0MA"
    consumer_secret = "5kKGsEAG23SAFlWy4e8UB02LmDSV9BoDXqyL6NUtxNg"

    # In the long run, we probably want to have the user authenticate with
    # their twitter handle. For now, this is a proof of concept. Use the app
    # account.
    key    = "600239400-Re2J1Q6ZpINrzpjHFOwH9G67IDOPiysDfrKHTZbP"
    secret = "gFxBtgjn4TH18frYiNySolCUo5SGV49UIMbLwKmQGY"

    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(key, secret)

    api = tweepy.API(auth)

    associations, _ = TwitterAssociation.get_or_create(url)
    for handle in associations.handles:
        # Assume messages are 120 characters or less
        # because usernames can be up to 20 characters
        api.update_status("@%s %s" % (handle, message))

class ReEngageControlPanel(URIHandler):
    def get(self, network=None):
        if not network:
            network = "fb"

        self.response.out.write(self.render_page('control_panel.html', {
            "network": network
        }))

class ReEngageProduct(URIHandler):
    def get(self):
        self.response.out.write(self.render_page('product.html', {
            "host": self.request.host_url
        }))

class ReEngageFindTweet(URIHandler):
    def get(self):
        self.post()

    def post(self):
        url   = self.request.get("url")
        now   = (self.request.get("now", "false") == "true")

        if now:
            logging.info("URL: %s" % url)

            users = _Twitter_find_user_by_query(url)
            logging.info("Users: %s" % users)

            _Twitter_associate_user(url, users)
        else:
            logging.info("Putting on task queue...")
            params = {
                "url": url,
                "now": "true"
            }
            taskqueue.add(url=build_url('ReEngageFindTweet'),
                          countdown=30, params=params)

        self.response.out.write ("200 OK")

class ReEngage(URIHandler):
    def get(self, network=None):
        if not network:
            network = "fb"

        message = self.request.get("message", "")
        template_values = {
            "message": message,
            "host": self.request.host_url,
            "network": network
        }
        self.response.out.write(self.render_page('%s.html' % network,
                                                 template_values))

    def post(self, network=None):
        networks = {
            "fb": self._FB_ReEngage,
            "t" : self._Twitter_ReEngage,
        }

        networks.get(network, "fb")()

    def _Twitter_ReEngage(self):
        url     = self.request.get("url")
        message = self.request.get("message", url)

        _Twitter_post(message, url)

        self.redirect(build_url("ReEngageControlPanel", "t"))
        return

    def _FB_ReEngage(self):
        url     = self.request.get("url")
        message = self.request.get("message", "Remember me?")

        # get an access token
        token = _FB_get_access_token()

        if not token:
            message = {
                "message": "Your application seems to be misconfigured."
            }
            self.redirect(build_url("ReEngageControlPanel", "fb",
                                    qs=message))
            return

        # get the id of the page
        page_id = _FB_get_page_id(url)

        if not page_id:
            message = {
                "message": "We couldn't message the page you requested."
            }
            self.redirect(build_url("ReEngageControlPanel", "fb",
                                    qs=message))
            return

        # post the message
        success = _FB_post(message, page_id, token)

        if not success:
            message = {
                "message": "There was a problem posting the message."
            }
            self.redirect(build_url("ReEngageControlPanel", "fb",
                                    qs=message))
            return

        message = {
            "message": "Message sent successfully!"
        }

        self.redirect(build_url("ReEngageControlPanel", "fb",
                                qs=message))
        return








