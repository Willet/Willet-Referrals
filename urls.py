#!/usr/bin/env python

import sys

# generic URL router for willet
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import memcache
from google.appengine.dist import use_library

from util.consts import *
from util.helpers import *

from apps.gae_bingo.middleware import GAEBingoWSGIMiddleware

use_library('django', '0.96')

# our intelligent uri router

def main():
    old_len = 0
    new_len = 0
    reload_uris = memcache.get('reload_uris')
    import_error = False
    
    try:
        combined_uris = memcache.get('combined_uris')
    except:
        reload_uris   = True
        combined_uris = False

    if reload_uris or not combined_uris:
        # if we have no uris, or if we are rewriting
        logging.info('reloading uris %s %s' % (reload_uris, combined_uris))
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
                    raise Exception('url route conflict with %s' % app)
            except Exception, e:
                logging.error('error importing %s: %s' % (app, e), exc_info=True)
                import_error = True

        if import_error:
            reload_uris = True
        else:
            reload_uris = False

        memcache.set('combined_uris', combined_uris)
        memcache.set('reload_uris', reload_uris)
    else:
        logging.info('using memcached uris!')

    #logging.info('running application with patterns: %s' % combined_uris)

    try:
        application = webapp.WSGIApplication(
            combined_uris,
            debug=USING_DEV_SERVER
        )
    
        # insert GAEBingo middlewhere
        application = GAEBingoWSGIMiddleware(application)

        run_wsgi_app(application)
    except:
        logging.error('There was an error running the application', exc_info=True)
        raise Exception('we need to fix something')

if __name__ == '__main__':
    main()

