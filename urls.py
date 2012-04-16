#!/usr/bin/env python

import logging
import sys

# generic URL router for willet
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import memcache

from util.consts import INSTALLED_APPS, USING_DEV_SERVER

from apps.gae_bingo.middleware import GAEBingoWSGIMiddleware

# our intelligent uri router

def main():
    """ Starts the webapp.
    
    If the reload_uris flag is set to true, a new URL map will be regenerated
    using urls.py of all INSTALLED_APPS.
    """
    import_error = False
    new_len = 0
    old_len = 0

    try:
        reload_uris = memcache.get('reload_uris')
    except AttributeError:
        reload_uris = False

    try:
        combined_uris = memcache.get('combined_uris')
    except AttributeError:
        reload_uris   = True
        combined_uris = False

    if reload_uris or not combined_uris:
        # if we have no uris, or if we are rewriting
        logging.info('reloading uris %r' % (reload_uris))
        combined_uris = []
        for app in INSTALLED_APPS: # INSTALLED_APPS came from consts.py
            try:
                import_str = 'apps.%s.urls' % app
                __import__(import_str, globals(), locals(), [], -1)
                app_urls = sys.modules[import_str]
                combined_uris.extend(app_urls.urlpatterns)

                old_len = new_len
                new_len = len(combined_uris)

                if old_len + len(app_urls.urlpatterns) > new_len:
                    # we clobbered some urls
                    raise ImportError('url route conflict with %s' % app)
            except ImportError, err:
                logging.error('error importing %s: %s' % (app, err), 
                              exc_info=True)
                import_error = True

        reload_uris = bool(import_error)

        memcache.set('combined_uris', combined_uris)
        memcache.set('reload_uris', reload_uris)

    application = webapp.WSGIApplication(combined_uris,
                                         debug=USING_DEV_SERVER)
    # insert GAEBingo middlewhere
    application = GAEBingoWSGIMiddleware(application)

    run_wsgi_app(application)

if __name__ == '__main__':
    main()

