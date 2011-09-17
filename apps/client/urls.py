#!/usr/bin/env python
#from apps.client.processes import *
from apps.client.views import *

urlpatterns = [
    (r'/client/account',  ShowAccountPage),
    (r'/client/login',    ShowLoginPage),
    (r'/client/logout',   Logout),
    (r'/client/auth',     DoAuthenticate),
    (r'/client/register', DoRegisterClient),
]
