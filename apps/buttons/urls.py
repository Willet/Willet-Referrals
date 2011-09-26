#!/usr/bin/env python
from apps.buttons.processes import *
from apps.buttons.views import *

urlpatterns = [
    (r'/b/load/(.*)', ButtonLoader),
    (r'/b/edit/(.*)/ajax/', EditButtonAjax),
    (r'/b/edit/(.*)/', EditButton),
    (r'/b/', ListButtons),
]

