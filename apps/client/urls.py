#!/usr/bin/env python
#from apps.client.processes import *
from apps.client.views import *

urlpatterns = [
    (r'/account', ShowAccountPage),
    (r'/auth', DoAuthenticate),
    (r'/login', ShowLoginPage),
    (r'/logout', Logout),
    (r'/register', DoRegisterClient),
]
