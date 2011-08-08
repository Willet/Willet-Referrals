import os
from urlparse import urlunsplit

# Product Stuff
NAME = 'ReferredU'

# Domain Stuff
USING_DEV_SERVER    = True if 'Development' in os.environ.get('SERVER_SOFTWARE', "") else False
PROTOCOL            = 'http' 
APP_DOMAIN          = 'None' if USING_DEV_SERVER else 'sy-willet.appspot.com'
DOMAIN              = os.environ['HTTP_HOST'] if USING_DEV_SERVER else APP_DOMAIN 
URL                 = urlunsplit((PROTOCOL, DOMAIN, '', '', '')) 

# Campaign Stuff
LANDING_CAMPAIGN_UUID = '28e530db44bf45e5'

# Twitter Stuff
TWITTER_SEARCH_URL = 'http://search.twitter.com/search.json?'
TWITTER_KEY = 'AGjI5z0RZFX7pq3i7nJgtg'
TWITTER_SECRET = 'aCUHHM1ZWcM4z35OORhbPuzIEsGlEB2QIl8Ysl3xn1o'

# Mixpanel Stuff
MIXPANEL_API_KEY = 'a4bed9e726adf0a972fe2277784b6f51'
MIXPANEL_API_URL = 'http://api.mixpanel.com/track/?'
MIXPANEL_SECRET  = 'd1c0a8833b32d0922f6ef91704925b5f'
MIXPANEL_TOKEN   = '5e7c1fdd252ecdccfecf1682df9f76a2'

# Facebook Stuff
FACEBOOK_APP_ID = '175144029215141'
FACEBOOK_APP_SECRET = '49fb2c41881e4f5aafe16b3dffdd9c0b'

# Klout Stuff
KLOUT_API_KEY = '6gs66hdaj6vmung5mtg3aeka'
KLOUT_API_URL = 'http://api.klout.com/1/users/show.json'

# Google Social Graph API Stuff
GOOGLE_SOCIAL_GRAPH_API_URL = 'https://socialgraph.googleapis.com/otherme?'

# LilCookies (secure cookies) Stuff
COOKIE_SECRET = 'f54eb793d727492e99601446aa9b06bab504c3d37bc54c8391f385f0dde03732'
