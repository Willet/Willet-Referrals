#!/usr/bin/env python

from apps.email.views import *
from apps.email.processes import *
from apps.email.models import *

urlpatterns = [
    (r'/email/sendasync', SendEmailAsync),
    (r'/test', SkypeCallTestingService),
]
