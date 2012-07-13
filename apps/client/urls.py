#!/usr/bin/env python

from apps.client.processes import *
from apps.client.views import *

urlpatterns = [
    (r'/client.json', ClientJSONDynamicLoader),
]