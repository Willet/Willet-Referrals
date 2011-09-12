#!/usr/bin/env python

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc"

import re, urllib

from django.utils import simplejson as json
from google.appengine.api import urlfetch, memcache
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app
from time import time

from apps.campaign.models import Campaign, get_campaign_by_id
from apps.link.models import Link, get_link_by_willt_code
from apps.user.models import get_user_by_cookie

from util.helpers import *
from util.urihandler import URIHandler
from util.consts import *

