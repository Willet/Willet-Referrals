#!/usr/bin/env python
from apps.admin.processes import *
from apps.admin.views import *

urlpatterns = [
    (r'/admin', Admin),
    (r'/renamefb', RenameFacebookData),
    (r'/renameinit', InitRenameFacebookData),
    (r'/cleanBadLinks', CleanBadLinks),
]

