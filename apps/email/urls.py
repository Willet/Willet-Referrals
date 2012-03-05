#!/usr/bin/env python

from apps.email.views import *
from apps.email.processes import *

urlpatterns = [
    (r'/email/everyone', EmailEveryone),
    (r'/email/someone', EmailSomeone) # taskqueue URL. do not call!
]
