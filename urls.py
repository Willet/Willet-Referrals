#!/usr/bin/env python

import sys

# generic URL router for willet
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

from util.consts import *
from util.helpers import *

from apps.gae_bingo.middleware import GAEBingoWSGIMiddleware

# our intelligent uri router

def main():
    combined_uris = []
    old_len = 0
    new_len = 0
    for app in INSTALLED_APPS:
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
