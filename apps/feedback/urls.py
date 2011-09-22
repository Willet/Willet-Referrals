#!/usr/bin/env python

from apps.feedback.views      import *
from apps.feedback.processes import * 

urlpatterns = [
    (r'/feedback/add', AddFeedback),
    (r'/feedback/add/task', AddFeedbackTask),
]
