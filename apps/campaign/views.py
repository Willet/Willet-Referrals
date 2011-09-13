#!/usr/bin/env python
__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc."

import hashlib, re, datetime

from django.utils import simplejson as json
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api.datastore_errors import BadValueError

from apps.client.models   import Client, get_client_by_email, authenticate, register
from apps.app.models import get_app_by_id, App
from apps.feedback.models import Feedback
from apps.stats.models import Stats
from apps.user.models import User, get_user_by_cookie, get_user_by_uuid
from apps.link.models import Link
from apps.conversion.models import Conversion

from util.helpers    import *
from util.urihandler import URIHandler
from util.consts     import *
from util.gaesessions import get_current_session






