#!/usr/bin/python

# Prepare the datastore for use

__author__      = "Sy Khader"
__copyright__   = "Copyright 2011, The Willet Corporation"

from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

# models
from models.link import CodeCounter
from util.consts import *

class InitCodes( webapp.RequestHandler ):
    """Run this script to initialize the counters for the willt
       url code generators"""

    def get(self):
        n = 0
        for i in range(20):
            ac = CodeCounter(count=i,
                             total_counter_nums=20,
                             key_name = str(i))
            ac.put()
            n += 1
        self.response.out.write(str(n) + " counters initialized")

def main():
    application = webapp.WSGIApplication([
        (r'/init/codes', InitCodes)], debug=USING_DEV_SERVER)
    run_wsgi_app(application)

if __name__ == "__main__":
    main()

