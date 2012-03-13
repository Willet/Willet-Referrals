#!/usr/bin/python

# consts.py
# constants for referrals

import os
import logging

from urlparse import urlunsplit

# Product Stuff
NAME = 'Willet'

# Domain Stuff
USING_DEV_SERVER    = True if 'Development' in os.environ.get('SERVER_SOFTWARE', "") else False
PROTOCOL            = 'http' 
SECURE_PROTOCOL     = 'https'
APP_DOMAIN          = 'None' if USING_DEV_SERVER else 'social-referral.appspot.com'
DOMAIN              = os.environ['HTTP_HOST'] if USING_DEV_SERVER else APP_DOMAIN 
URL                 = urlunsplit((PROTOCOL, DOMAIN, '', '', '')) # no trailing slash
SECURE_URL          = urlunsplit((SECURE_PROTOCOL, DOMAIN, '', '', '')) 
KEYS                = os.environ['HTTP_HOST']

# Our BS P3P Header
#P3P_HEADER = 'CP="NOI DSP LAW DEVo IVDo OUR STP ONL PRE NAV"'
#P3P_HEADER = 'CP="NON DSP ADM DEV PSD IVDo OUR IND STP PHY PRE NAV UNI"'
P3P_HEADER = 'CP="IDC DSP COR ADM DEVi TAIi PSA PSD IVAi IVDi CONi HIS OUR IND CNT"'

# Campaign Stuff
LANDING_CAMPAIGN_UUID  = '28e530db44bf45e5'
LANDING_CAMPAIGN_STORE = '962072'
FACEBOOK_QUERY_URL = 'https://graph.facebook.com/'

# Demo BUTTONS Facebook app id
BUTTONS_FACEBOOK_APP_ID = '166070566811816'
BUTTONS_FACEBOOK_APP_SECRET = '1f8e4c81de61de9dc054685bddf8b50f'

# Facebook Stuff
FACEBOOK_APP_ID     = '181838945216160'
FACEBOOK_APP_SECRET = 'a34a3f5ba2d87975ae84dab0f2a47453'
    
# Mixpanel Stuff (Legacy)
MIXPANEL_API_KEY = 'a4bed9e726adf0a972fe2277784b6f51'
MIXPANEL_API_URL = 'http://api.mixpanel.com/track/?'
MIXPANEL_SECRET  = 'd1c0a8833b32d0922f6ef91704925b5f'
MIXPANEL_TOKEN   = '5e7c1fdd252ecdccfecf1682df9f76a2'

# Google Social Graph API Stuff
GOOGLE_SOCIAL_GRAPH_API_URL = 'https://socialgraph.googleapis.com/otherme?'

# LilCookies (secure cookies) Stuff
COOKIE_SECRET = 'f54eb793d727492e99601446aa9b06bab504c3d37bc54c8391f385f0dde03732'

SHOPIFY_APPS = {
    'SIBTShopify': {
        'api_key': 'b153f0ccc9298a8636f92247e0bc53dd',
        'api_secret': '735be9bc6b3e39b352aa5c287f4eead5',
        'class_name': 'SIBTShopify',
        'facebook': {
            'app_id': '132803916820614',
            'app_secret': '59a1dbe26a27e72ea32395f2e2d434e0'
        }
    }, 'WOSIBShopify': {
        # repeat keys in SIBT
        'api_key': 'b153f0ccc9298a8636f92247e0bc53dd',
        'api_secret': '735be9bc6b3e39b352aa5c287f4eead5',
        'class_name': 'WOSIBShopify',
        'facebook': {
            'app_id': '132803916820614',
            'app_secret': '59a1dbe26a27e72ea32395f2e2d434e0'
        }
    }, 'ButtonsShopify': {
        'api_key': 'ec07b486dee3ddae870ef082ac6a748f', 
        'api_secret': '1076f41726eb9811ac925a0a8b7c4586', 
        'class_name': 'ButtonsShopify'       
    }
}

# Shopify Stuff
REFERRAL_SHOPIFY_API_KEY = 'c46f84fb6458a72c774504ba372757f1' 
REFERRAL_SHOPIFY_API_SHARED_SECRET = '82e2c5a9d210be294c046b7bc9ff55eb' 

SIBT_SHOPIFY_API_KEY = 'b153f0ccc9298a8636f92247e0bc53dd'
SIBT_SHOPIFY_API_SHARED_SECRET = '735be9bc6b3e39b352aa5c287f4eead5'

BUTTONS_SHOPIFY_API_KEY = '5fe8fa18137ddfc5912de35428f738a1'
BUTTONS_SHOPIFY_API_SHARED_SECRET = '9aca00dc207a002e499694355cd71882'

# controls the number of memcache buckets
# and the maximum length of a bucket before it gets put to datastore
NUM_ACTIONS_MEMCACHE_BUCKETS = 20
MEMCACHE_BUCKET_COUNTS = {
    'default': 20,
    '_willet_actions_bucket': 25,
    '_willet_user_ips_bucket': 20,
    '_willet_user_put_bucket': 20,
}

# number of seconds to memcache an item
# see: http://stackoverflow.com/questions/2793366/what-is-the-maximum-length-in-seconds-to-store-a-value-in-memcache
# TODO: Try 2591999 instead
MEMCACHE_TIMEOUT = 1728000

# List of root template directories
# to import templates from
TEMPLATE_DIRS = (
    'apps/homepage/templates',        
)

# Admin whitelist
ADMIN_EMAILS = [ 'harrismc@gmail.com', 'matt@getwillet.com',
                 'fraser.harris@gmail.com', 'fraser@getwillet.com',
                 'b2lai@uwaterloo.ca', 'lpppppl@gmail.com', 'brian@getwillet.com',
                 'nicholas.terwoord@gmail.com', 'nicholas@getwillet.com' ]

ADMIN_IPS = [ '70.83.160.171',      # Notman House
              '69.166.16.20',       # VeloCity @ Hub
              '216.16.232.86',      # Brian Desktop network drop
              '206.126.92.56'       # Brian House
            ]

# the apps we are using
INSTALLED_APPS = [
    'admin',
    'app',
    'app.shopify',
    'analytics_backend',
    'buttons',
    'buttons.shopify',
    'client',
    'client.shopify',
    'email',
    'gae_bingo',
    'gae_bingo.tests',
    'homepage',
    'order',
    'order.shopify',
    'product',
    'product.shopify',
    'sibt',
    'sibt.shopify',
    'wosib',
    'wosib.shopify',
    'user',
    # LINK MUST ALWAYS BE LAST
    'link',
]

# Overide settings with local_consts
try:
    from local_consts import *
except Exception, e:
    logging.info('no local_consts.py: %s' % e, exc_info=True)
    pass
