#!/usr/bin/env python

from django.utils import simplejson as json
from google.appengine.api import urlfetch, memcache
from google.appengine.ext import webapp
from google.appengine.api import taskqueue
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

from google.appengine.api import apiproxy_stub_map
from google.appengine.api import runtime

def shutdown_hook():
    apiproy_stub_map.apiproxy.CancelApiCalls()
    save_state()
    # May want to raise an exception
    

def start():
    pass

def run():
    while not runtime.is_shutting_down():
        # do something
        break 

runtime.set_shutdown_hook(my_shutdown_hook)
