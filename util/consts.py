import os
from urlparse import urlunsplit

# Product Stuff
NAME = 'ReferredU'

# Domain Stuff
USING_DEV_SERVER    = True if 'Development' in os.environ.get('SERVER_SOFTWARE', "") else False
PROTOCOL            = 'http' 
APP_DOMAIN          = 'None' if USING_DEV_SERVER else 'social-referral.appspot.com'
DOMAIN              = os.environ['HTTP_HOST'] if USING_DEV_SERVER else 'www.' + APP_DOMAIN 
URL                 = urlunsplit((PROTOCOL, DOMAIN, '', '', '')) 

# Campaign Stuff
LANDING_CAMPAIGN_UUID = '28e530db44bf45e5'

# Twitter Stuff
TWITTER_SEARCH_URL = 'http://search.twitter.com/search.json?'
TWITTER_KEY = '2O3uHYkLKlHdy2PECgP3Q'
TWITTER_SECRET = 'W3fe6c1ZP3D4RyymqszxXfNcJzvu0fN82Nf3S68078'

# Mixpanel Stuff
MIXPANEL_API_KEY = '2792aa08e5efaf4e406d8a4ac224565d'
MIXPANEL_API_URL = 'http://api.mixpanel.com/track/?'
MIXPANEL_SECRET  = '27da75953193e14e626d67906b1a5148'
MIXPANEL_TOKEN   = '8e365da676bb7e48929dfb9e649cf9d4'

# Facebook Stuff
FACEBOOK_APP_ID = '181838945216160'
FACEBOOK_APP_SECRET = 'a34a3f5ba2d87975ae84dab0f2a47453'

# Klout Stuff
KLOUT_API_KEY = '6gs66hdaj6vmung5mtg3aeka'
KLOUT_API_URL = 'http://api.klout.com/1/users/show.json'

# Google Social Graph API Stuff
GOOGLE_SOCIAL_GRAPH_API_URL = 'https://socialgraph.googleapis.com/otherme?'

# LilCookies (secure cookies) Stuff
COOKIE_SECRET = 'f54eb793d727492e99601446aa9b06bab504c3d37bc54c8391f385f0dde03732'
