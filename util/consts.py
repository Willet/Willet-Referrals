#!/usr/bin/python

# consts.py
# constants for referrals

import os
from urlparse import urlunsplit

# Product Stuff
NAME = 'ReferredU'

# Domain Stuff
USING_DEV_SERVER    = True if 'Development' in os.environ.get('SERVER_SOFTWARE', "") else False
PROTOCOL            = 'http' 
APP_DOMAIN          = 'None' if USING_DEV_SERVER else 'social-referral.appspot.com'
DOMAIN              = os.environ['HTTP_HOST'] if USING_DEV_SERVER else APP_DOMAIN 
URL                 = urlunsplit((PROTOCOL, DOMAIN, '', '', '')) 
KEYS                = os.environ['HTTP_HOST']


# Campaign Stuff
LANDING_CAMPAIGN_UUID = '28e530db44bf45e5'
FACEBOOK_QUERY_URL='https://graph.facebook.com/'

if os.environ['HTTP_HOST'] == 'sy-willet.appspot.com':
    # Twitter Stuff
    TWITTER_SEARCH_URL = 'http://search.twitter.com/search.json?'
    TWITTER_KEY = 'AGjI5z0RZFX7pq3i7nJgtg'
    TWITTER_SECRET = 'aCUHHM1ZWcM4z35OORhbPuzIEsGlEB2QIl8Ysl3xn1o'
    
    # Facebook Stuff
    FACEBOOK_APP_ID = '175144029215141'
    FACEBOOK_APP_SECRET = '49fb2c41881e4f5aafe16b3dffdd9c0b'
    
    # LINKEDIN API JAZZ
    LINKEDIN_KEY = 'j2isiwa49dkz'
    LINKEDIN_SECRET = 'n0RRpGLCvVFvufdG'

else:
    # Twitter Stuff
    TWITTER_SEARCH_URL = 'http://search.twitter.com/search.json?'
    TWITTER_KEY        = '2O3uHYkLKlHdy2PECgP3Q'
    TWITTER_SECRET     = 'W3fe6c1ZP3D4RyymqszxXfNcJzvu0fN82Nf3S68078'
    
    # Facebook Stuff
    FACEBOOK_APP_ID     = '141990385884645'
    FACEBOOK_APP_SECRET = '4077e465d5d50e87aa0fbd2d472f60ea'
    
# LINKEDIN API JAZZ
LINKEDIN_KEY    = 'j2isiwa49dkz'
LINKEDIN_SECRET = 'n0RRpGLCvVFvufdG'

# Mixpanel Stuff
MIXPANEL_API_KEY = 'a4bed9e726adf0a972fe2277784b6f51'
MIXPANEL_API_URL = 'http://api.mixpanel.com/track/?'
MIXPANEL_SECRET  = 'd1c0a8833b32d0922f6ef91704925b5f'
MIXPANEL_TOKEN   = '5e7c1fdd252ecdccfecf1682df9f76a2'

# Klout Stuff
KLOUT_API_KEY = '6gs66hdaj6vmung5mtg3aeka'
KLOUT_API_URL = 'http://api.klout.com/1/users/show.json'

# Google Social Graph API Stuff
GOOGLE_SOCIAL_GRAPH_API_URL = 'https://socialgraph.googleapis.com/otherme?'

# LilCookies (secure cookies) Stuff
COOKIE_SECRET = 'f54eb793d727492e99601446aa9b06bab504c3d37bc54c8391f385f0dde03732'

# Shopify Stuff
SHOPIFY_API_KEY = '35e9a42e1ba8601b0be820a58b181693'
SHOPIFY_API_PASSWORD = '38bf7ff0e9d42f55a08dbd986453bb49'
