import logging
from urllib import urlencode
from urlparse import urlparse
from google.appengine.api import urlfetch
from google.appengine.api.taskqueue import taskqueue
import re
from apps.reengage.models import TwitterAssociation, PinterestAssociation
from util import httplib2
from util.urihandler import URIHandler
from util.local_consts import SHOPIFY_APPS
from django.utils import simplejson as json
from util.helpers import url as build_url
from util import tweepy
from util.BeautifulSoup import BeautifulSoup

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

def _Pin_find_pins_for_site(site, pin_msg):
    """ Gets pins for a given site with a given message.

    `site` is expected to just be the domain name of the site (no protocol,
    or path).
    `pin_msg` is expected to not contain `site`
    """

    # Visit pinterest.com/source/{site}
    url = "http://pinterest.com/source/%s" % site
    if url[-1] != "/":
        url = "%s/" % url

    logging.info("URL: %s\nSite: %s" % (url, site))

    resp = urlfetch.fetch(url)
    soup = BeautifulSoup(resp.content)

    # Find pins that contain pin_msg
    # Regex won't work if truncated!
    r       = re.compile(".*%s.*%s.*" % (pin_msg, site), re.DOTALL)
    logging.info("Message: %s\nSite:%s" % (pin_msg, site))

    pin_gen = (p for p in soup.findAll(True, 'pin') if r.match(p.prettify()))
    pins    = [pin.get("data-id") for pin in pin_gen]

    return list(set(filter(None, pins)))

def _Pin_associate_user(url, users):
    associations, _ = PinterestAssociation.get_or_create(url)
    for user in users:
        if user not in associations.pins:
            associations.pins.append(user)

    associations.put()

def _Pin_comment(message, url):
    login_url = "https://pinterest.com/login/?next=%2F"

    # Scrape login page
    h = httplib2.Http()
    response, content = h.request(login_url, "GET")

    soup = BeautifulSoup(content)
    csrf = soup.find("input", {"name": "csrfmiddlewaretoken"}).get("value")

    if not csrf:
        return

    # Login
    headers = {
        'Content-type': 'application/x-www-form-urlencoded',
        'Cookie'      : response.get("Cookie", "")
    }
    body    = {
        'email'              : 'disposable@nt3r.com',
        'password'           : 'asdfghjkl',
        'csrfmiddlewaretoken': csrf
    }

    # 405: Method not allowed response, why?
    response, content = h.request(url, 'POST', headers=headers, body=urlencode(body))

    logging.info("Response: %s" % response)
    logging.info("Content : %s" % content)

    headers = {
        'Cookie'      : response.get('Set-Cookie', ""),
        'Content-type': 'application/x-www-form-urlencoded'
    }
    body    = {
        "text": message
    }

    # Post comment
    associations, _ = PinterestAssociation.get_or_create(url)
    for pin_id in associations.pins:
        referrer = "http://pinterest.com/pin/%s/" % pin_id # necessary?
        comments = "%scomment/" % referrer

        response, content = h.request(comments, 'POST', headers=headers,
                                      body=urlencode(body))
        logging.info("Response: %s" % response)
        logging.info("Content : %s" % content)


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

class ReEngageFindPin(URIHandler):
    def get(self):
        self.post()

    def post(self):
        url     = self.request.get("url")
        pin_msg = self.request.get("pin_msg")
        now     = (self.request.get("now", "false") == "true")

        if now:
            logging.info("URL: %s" % url)

            # Strip off protocol and path
            site = urlparse(url).netloc

            pin_ids = _Pin_find_pins_for_site(site, pin_msg)
            logging.info("Pins: %s" % pin_ids)

            _Pin_associate_user(url, pin_ids)
        else:
            logging.info("Putting on task queue...")
            params = {
                "pin_msg": pin_msg,
                "url"    : url,
                "now"    : "true"
            }
            taskqueue.add(url=build_url('ReEngageFindPin'),
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
            "p" : self._Pin_ReEngage,
        }

        networks.get(network, "fb")()

    def _Pin_ReEngage(self):
        url     = self.request.get("url")
        message = self.request.get("message", url)

        _Pin_comment(message, url)

        self.redirect(build_url("ReEngageControlPanel", "p"))
        return

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








