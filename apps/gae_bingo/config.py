from __future__ import absolute_import

from apps.user.models import get_user_by_cookie, get_emails_by_user

# CUSTOMIZE can_see_experiments however you want to specify
# whether or not the currently-logged-in user has access
# to the experiment dashboard.
def can_control_experiments( request_handler=None ):
    # Admin whitelist
    whitelist = [ 'barbara@getwillet.com', 'barbara@getwillet.ca', 'barbaraemac@gmail.com',
                  'foo@bar.com', 'asd@asd.com', 'z4beth@gmail.com', 'harrismch@gmail.com',
                  'fraser.harris@gmail.com' ]

    if request_handler:
        user = get_user_by_cookie( request_handler )

        emails = get_emails_by_user( user )
        for e in emails:
            if e.address in whitelist:
                return True

    # TODO: Make this false .. true only for testing
    return True

# CUSTOMIZE current_logged_in_identity to make your a/b sessions
# stickier and more persistent per user.
#
# This should return one of the following:
#
#   A) a db.Model that identifies the current user, like models.UserData.current()
#   B) a unique string that consistently identifies the current user, like users.get_current_user().user_id()
#   C) None, if your app has no way of identifying the current user for the current request. In this case gae_bingo will automatically use a random unique identifier.
#
# Ideally, this should be connected to your app's existing identity system.
#
# To get the strongest identity tracking even when switching from a random, not logged-in user
# to a logged in user, return a model that inherits from GaeBingoIdentityModel.
# See docs for details.
#
# Examples:
#   return models.UserData.current()
#         ...or...
#   from google.appengine.api import users
#   return users.get_current_user().user_id() if users.get_current_user() else None
def current_logged_in_identity():
    return None # TODO
    #return users.get_current_user().user_id() if users.get_current_user() else None
