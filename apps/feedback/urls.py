#!/usr/bin/env python
from apps.feedback.views import *

urlpatterns = [
    (r'/feedback/doFeedback', DoAddFeedback),
]
