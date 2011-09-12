#!/usr/bin/env python

# generic URL router for willet
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

try:
    from apps.campaign.models import *
except Exception,e:
    logging.error('error importing %s' % e)

from util.consts import *
from util.helpers import *
from util.urihandler import URIHandler

# our intelligent uri router
def main():
    combined_uris = []
    for app in INSTALLED_APPS:
        try:
            import_str = 'apps.%s.urls' % app
            #__import__(import_str)
            #urls = sys.modules[import_str]
            old_len = len(combined_uris)
            module = __import__(import_str, globals(), locals(), [], -1)
            add_len = len(module.urlpatterns)
            combined_uris.extend(module.urlpatterns)
            new_len = len(combined_uris)

            if old_len + add_len > new_len:
                # we clobbered some urls
                raise Exception('url route conflict with %s' % app)
        except Exception,e:
            logging.error('error importing %s: %s' % (app, e))
    
    application = webapp.WSGIApplication(
        combined_uris,
        debug=USING_DEV_SERVER
    )
    run_wsgi_app(application)

if __name__ == '__main__':
    main()
