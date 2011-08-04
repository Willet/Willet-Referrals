import os
from urlparse import urlunsplit

# Domain Stuff
USING_DEV_SERVER    = True if 'Development' in os.environ.get('SERVER_SOFTWARE', "") else False
PROTOCOL            = 'http' 
APP_DOMAIN          = 'None' if USING_DEV_SERVER else 'wil.lt'
DOMAIN              = os.environ['HTTP_HOST'] if USING_DEV_SERVER else 'www.' + APP_DOMAIN 
URL                 = urlunsplit((PROTOCOL, DOMAIN, '', '', '')) 

# Campaign Stuff
LANDING_CAMPAIGN_UUID = 'e179cc102f904c92'

# Twitter Stuff
TWITTER_SEARCH_URL = 'http://search.twitter.com/search.json?'

# Mixpanel Stuff
MIXPANEL_API_KEY = '2792aa08e5efaf4e406d8a4ac224565d'
MIXPANEL_API_URL = 'http://api.mixpanel.com/track/?'
MIXPANEL_SECRET  = '27da75953193e14e626d67906b1a5148'
MIXPANEL_TOKEN   = '8e365da676bb7e48929dfb9e649cf9d4'


# Facebook Stuff
FACEBOOK_APP_ID = '181838945216160'
FACEBOOK_APP_SECRET = 'a34a3f5ba2d87975ae84dab0f2a47453'

