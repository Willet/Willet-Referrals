#!/usr/bin/env python
from apps.app.views import *
from apps.app.processes import *

urlpatterns = [
    # Views
    #(r'/a/shopify',   ShopifyRedirect),
    (r'/a/deleteApp', DoDeleteApp),
    (r'/app.json', AppJSONDynamicLoader),

    # Processes
    (r'/a/appClicksCounter', AppClicksCounter),
    (r'/a/batchRequest', BatchRequest),
    (r'/a/storeSurvey', BatchStoreSurvey)
]