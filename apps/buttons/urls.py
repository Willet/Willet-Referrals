#!/usr/bin/env python
from apps.buttons.processes import *
from apps.buttons.views import *

urlpatterns = [
    (r'/b/action/(.*)/(.*)/', ButtonsAction),
]

