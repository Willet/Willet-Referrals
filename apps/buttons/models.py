#!/usr/bin/env python

# Buttons model
# Extends from "App"

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc"

from google.appengine.ext import db

from apps.app.models import App

from util.model import Model

NUM_VOTE_SHARDS = 15


class Buttons(App):
    """Clients install the buttons App"""  

    title_selector       = db.StringProperty()
    description_selector = db.StringProperty()
    image_selector       = db.StringProperty()
    button_selector      = db.StringProperty()

    def __init__(self, *args, **kwargs):
        """ Initialize this model """
        super(Buttons, self).__init__(*args, **kwargs)

    def _validate_self(self):
        return True


# TODO delete these deprecated functions after April 18, 2012 (1 month warning)
def get_buttons_app_by_uuid(id):
    raise DeprecationWarning('Replaced by Buttons.get_by_uuid')
    return Buttons.get_by_uuid(id)

def get_buttons_app_by_client(client):
    raise DeprecationWarning('Replaced by Buttons.get_by_client')
    return Buttons.get_by_client(client)
