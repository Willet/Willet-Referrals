#!/usr/bin/env python
from apps.buttons.processes import *
from apps.buttons.views import *

urlpatterns = [
    (r'/b/load/(.*)', ButtonsJS),
    (r'/b/edit/(.*)/ajax/', EditButtonAjax),
    (r'/b/edit/(.*)/', EditButton),
    (r'/b/action/(.*)/(.*)/', ButtonsAction),
    (r'/b/', ListButtons),
]

