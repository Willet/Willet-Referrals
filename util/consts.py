#!/usr/bin/python

# consts.py
# constants for referrals

import os
from urlparse import urlunsplit

# Product Stuff
NAME = 'Willet Juice'

# Domain Stuff
USING_DEV_SERVER    = True if 'Development' in os.environ.get('SERVER_SOFTWARE', "") else False
PROTOCOL            = 'http' 
APP_DOMAIN          = 'None' if USING_DEV_SERVER else 'social-referral.appspot.com'
DOMAIN              = os.environ['HTTP_HOST'] if USING_DEV_SERVER else APP_DOMAIN 
URL                 = urlunsplit((PROTOCOL, DOMAIN, '', '', '')) 
KEYS                = os.environ['HTTP_HOST']

# Campaign Stuff
LANDING_CAMPAIGN_UUID  = '28e530db44bf45e5'
LANDING_CAMPAIGN_STORE = '962072'
FACEBOOK_QUERY_URL='https://graph.facebook.com/'
TWITTER_SEARCH_URL = 'http://search.twitter.com/search.json?'

# Twitter Stuff
TWITTER_KEY        = '2O3uHYkLKlHdy2PECgP3Q'
TWITTER_SECRET     = 'W3fe6c1ZP3D4RyymqszxXfNcJzvu0fN82Nf3S68078'
TWITTER_TIMELINE_URL = 'https://api.twitter.com/1/statuses/user_timeline.json?'    

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
SHOPIFY_API_KEY = '3337f51dd5d202486d360773a4c29db4' #'c38cec921dd34143f581c9c889527d55' #'2b9850499a01972490e5ddd79aa03b1c'
SHOPIFY_API_SHARED_SECRET = 'caf09e36b7bbaccda5210983c7e234ed' #'74a8223c64027a259add577dab98e403' #'0531f9818eb9eecaee6160583df9eea3'

INSTALLED_APPS = [
    'admin',
    'app',
    'client',
    'homepage',
    'mixpanel',
    'oauth',
    'order',
    'referral',
    'referral.shopify',
    'sibt',
    'stats',
    'testimonial',
    'user',
    'user_analytics',
    # LINK MUST ALWAYS BE LAST
    'link',
]

# Overide settings with local_consts
#try:
from local_consts import *
#except:
    #logging.error('no local_consts.py')
    #pass

