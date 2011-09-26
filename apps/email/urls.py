#!/usr/bin/env python

from apps.email.views import *
from apps.email.processes import *

urlpatterns = [
    # Views
#    (r'/a/deleteApp', DoDeleteApp),

    # Processes
    (r'/email/sendEmailInvites', SendEmailInvites),
]
