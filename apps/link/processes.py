#!/usr/bin/env python

__author__      = "Sy Khader"
__copyright__   = "Copyright 2012, The Willet Corporation"

import logging
import urlparse

from google.appengine.ext import db

from apps.link.models import CodeCounter
from apps.link.models import Link
from apps.app.models import App

from util.helpers import set_clicked_cookie, is_blacklisted
from util.consts import APP_DOMAIN, P3P_HEADER, URL
from util.urihandler import URIHandler


class TrackWilltURL(URIHandler):
    """ Tracks click-throughs on a given code.

    It tests for the presence of a cookie that it also sets in order to ensure
    incremental click-throughs are unique.

    """
    def get( self, code ):
        self.response.headers.add_header('P3P', P3P_HEADER)
        logging.info("PATH %s" % self.request.url )
        if APP_DOMAIN not in self.request.url:
            self.redirect( '%s/%s' % (URL, code) )
            return

        # Fetch the Link
        link = Link.get_by_code(code)
        if not link:
            logging.warn ("no link contains the code '%s'" % code)
            self.redirect("/")
            return

        #  Let the App handle the 'click'
        if not is_blacklisted(self.request.headers['User-Agent']):
            logging.info("WHO IS THIS? -> " + self.request.headers['User-Agent'])

            link.app_.handleLinkClick( self, link )

            set_clicked_cookie(self.response.headers, code)
        return


class InitCodes(URIHandler):
    """Run this script to initialize the counters for the willt
       url code generators"""
    def get(self):
        n = 0
        for i in range(20):
            ac = CodeCounter(
                count=i,
                total_counter_nums=20,
                key_name = str(i)
            )
            ac.put()
            n += 1
        self.response.out.write(str(n) + " counters initialized")


class CleanBadLinks(URIHandler):
    """ Looks for links that are missing a user """
    def get(self):
        links = Link.all().filter('user =', None)

        count = 0
        result   = 'Cleaning the bad links'
        try:
            for l in links:
                clicks = l.count_clicks()
                try:
                    if l.user == None and clicks != 0:
                        count += 1
                        result   += "<p> URL: %s Clicks: %d Code: %s Campaign: %s Time: %s</p>" % (l.target_url, clicks, l.willt_url_code, l.campaign.title, l.creation_time)

                        l.delete()
                except Exception, e:
                    l.delete()
                    logging.warn('probably unable to resolve property: %s' % e)
        except TypeError:
            logging.warn("Expected <google.appengine.datastore.Key> or <google.appengine.ext.db.Model>, got an item in %r" % links)

        logging.info("CleanBadLinks Report: Deleted %d Links. (%s)" % ( count, result ) )


class IncrementCodeCounter(URIHandler):
    """ This was getting called every time a willet code was being
        created, usually taking ~100ms. Moved to a task to speed up
        page load times"""
    def post(self):
        def txn(cc):
            cc.count += cc.total_counter_nums
            cc.put()
            return cc

        count = self.request.get('count')
        cc = CodeCounter.all().filter('count =', int(count)).get()
        if cc != None:
            returned_cc = db.run_in_transaction(txn, cc)
            logging.info('incremented code counter %s' % returned_cc)


class CreateLink(URIHandler):
    """Creates a Link object that rediects to a given url.

    URL defaults to http://social-referral.appspot.com (to allow Links to be created prior
                                  to knowledge of destination)
    """
    def post(self):
        """See class docstring.

        If a code is given and a Link for that code is found, the Link's
        URL will be overwritten.

        This controller also supports GET. The GET version will
        redirect the browser to said URL.
        """
        url = self.request.get('url', 'http://social-referral.appspot.com')
        app = App.get(self.request.get('app_uuid', '')) or None
        code = self.request.get('code', '')
        link = create_link(url, app, code)

        self.response.out.write("%s" % link.willt_url_code)

    def get(self):
        """Creates/Modifies the link by URL, then redirects there."""
        link = self.post()
        if link:
            self.redirect(link.target_url)
        else:
            self.response.out.write("You're doing it wrong")


def create_link(url, app=None, code=None):
    """helper function for CreateLink. Used by other views and controllers."""
    link = None

    if code:
        link = Link.get_by_code(code)

    domain = urlparse.urlparse(url)
    if not (domain.scheme and domain.netloc):  # http and google.com
        logging.error('URL supplied (%s) is invalid' % url)
        return None

    if not link:  # create
        try:  # fails if url is not valid
            link = Link.create(targetURL=url,
                               app=app,
                               domain=domain)
        except AttributeError:
            logging.error('URL creation rejected (%s)' % url)
            return None
    else:  # update
        link.target_url = url
        link.origin_domain = domain

        link.memcache_by_code()
        link.put_later()  # Links aren't normally put like this

    return link  # could be nothing!