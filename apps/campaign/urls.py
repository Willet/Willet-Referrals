#!/usr/bin/env python
from apps.campaign.processes import *
from apps.campaign.views import *

urlpatterns = [
    (r'/campaignClicksCounter', CampaignClicksCounter),
    (r'/triggerCampaignAnalytics', TriggerCampaignAnalytics),
    (r'/computeCampaignAnalytics', ComputeCampaignAnalytics),
    (r'/code', ShowCodePage),
    (r'/edit', ShowEditPage),
    (r'/campaign/(.*)/', ShowCampaignPage),
    (r'/deleteCampaign', DoDeleteCampaign),
    (r'/doUpdateOrCreateCampaign', DoUpdateOrCreateCampaign),
    (r'/emailerCron', EmailerCron),
    (r'/emailerQueue', EmailerQueue),
]
