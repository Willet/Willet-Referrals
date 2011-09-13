#!/usr/bin/env python

import sys, traceback

# generic URL router for willet
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

from util.consts import *
from util.helpers import *
from util.urihandler import URIHandler

try:
    from apps.campaign.models import *
except Exception,e:
    logging.error('error importing %s' % e)


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
        except Exception,e:
            #exc_type, exc_value, exc_traceback = sys.exc_info()
            #tb = traceback.extract_tb(exc_traceback)
            logging.error('error importing %s: %s' % (app, e), exc_info=1)

    #logging.info('running application with patterns: %s' % combined_uris)

    application = webapp.WSGIApplication(
        combined_uris,
        debug=USING_DEV_SERVER
    )
    run_wsgi_app(application)

if __name__ == '__main__':
    main()
