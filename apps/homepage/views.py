#!/usr/bin/python

"""Renders "static" pages."""

__author__ = "Willet, Inc."
__copyright__ = "Copyright 2012, Willet, Inc."

from util.urihandler import URIHandler


class ShowLandingPage(URIHandler):
    """Renders the main template."""
    def get(self, page):
        """Renders the main template."""
        template_values = {}
        self.response.out.write(self.render_page('homepage/landing.html',
                                                 template_values))

class ShowPrivacyPage(URIHandler):
    """Renders the privacy page."""
    def get(self):
        """Renders the privacy page."""
        template_values = {}
        self.response.out.write(self.render_page('homepage/privacy.html',
                                                 template_values))