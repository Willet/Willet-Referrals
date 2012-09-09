#!/usr/bin/env python

"""Idempotent Code operations go here."""

__author__ = "Willet, Inc."
__copyright__ = "Copyright 2012, Willet, Inc"

import logging
from google.appengine.api import memcache

from apps.client.models import Client

from scss.scss import Scss
from util.urihandler import URIHandler


class SCSSPathCompiler(URIHandler):
    """Output a SCSS-compiled CSS file based on the file name."""
    def get(self, file_name=''):
        """Given file_name, render the scss file, templates/scss/file_name.

        Note the absence of file extension.
        """
        compiled = ''
        self.response.headers['Content-Type'] = 'text/css'

        if not file_name:
            logging.warn('no file specified')
            return

        # try to fetch memcached, compiled css for this scss file
        compiled = memcache.get(file_name) or ''
        if not compiled:
            logging.debug('regenerating css file.')
            try:
                css = Scss()
                compiled = css.compile(self.render_page(
                    'scss/%s' % file_name, {}))
                # save it so it doesn't need to compile all the time
                memcache.set(file_name, compiled)
            except Exception, err:
                # does it matter what? I won't be rendering you
                logging.error(err, exc_info=True)

        self.response.out.write(compiled)