#!/usr/bin/env python
from apps.mixpanel.processes import *
#from apps.mixpanel.views    import *

urlpatterns = [
    # processes
    (r'/mixpanel', SendToMixpanel),    
]

