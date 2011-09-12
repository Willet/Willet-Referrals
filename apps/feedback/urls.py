#!/usr/bin/env python
from apps.feedback.processes import *
from apps.feedback.views import *

urlpatterns = [
    (r'/doFeedback', DoAddFeedback),
]
