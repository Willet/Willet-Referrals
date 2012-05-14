#!/usr/bin/env python

from apps.sibt.shuuemura.views import *

urlpatterns = [
    (r'/s/shuuemura/sibt.js', SIBTShuuemuraServeScript),
]