#!/usr/bin/env python

from util.urihandler import DeprecationHandler

urlpatterns = [
    # Views
    (r'/s/js/jquery.colorbox.js',   DeprecationHandler),
    (r'/s/ask.html',                DeprecationHandler),
    (r'/s/ask-page.html',           DeprecationHandler),
    (r'/s/vote.html',               DeprecationHandler),
    (r'/s/results.html',            DeprecationHandler),
    (r'/s/fb_thanks.html',          DeprecationHandler),
    (r'/s/track/unload',            DeprecationHandler),
    (r'/s/shopify/real-sibt.js',    DeprecationHandler),
    (r'/s/sibt.js',                 DeprecationHandler),
    (r'/s/beta',                    DeprecationHandler),
    (r'/s/beta/signup',             DeprecationHandler),
    (r'/s/instances/status',        DeprecationHandler),

    # Processes
    (r'/s/doVote',                  DeprecationHandler),
    (r'/s/getExpired',              DeprecationHandler),
    (r'/s/instance/start',          DeprecationHandler),
    (r'/s/instance/products',       DeprecationHandler),
    (r'/s/removeExpired',           DeprecationHandler),
    (r'/s/sendFriendAsks',          DeprecationHandler),
]
