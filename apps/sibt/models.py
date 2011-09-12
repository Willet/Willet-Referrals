#!/usr/bin/python

# The 'Should I Buy This?' model
# Extends from "App"

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc"

import hashlib, logging, datetime

from django.utils         import simplejson as json
from google.appengine.ext import db

from models.app           import App
from util.consts          import *

class SIBT( App ):
   
    def __init__(self, *args, **kwargs):
        super(SIBT, self).__init__(*args, **kwargs)
    
