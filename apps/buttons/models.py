#!/usr/bin/env python

# Buttons model
# Extends from "App"

__author__ = "Willet, Inc."
__copyright__ = "Copyright 2011, Willet, Inc"

from google.appengine.ext import db

from apps.app.models import App

from util.model import Model

NUM_VOTE_SHARDS = 15


class Buttons(App):
    """Clients install the buttons App"""

    title_selector = db.StringProperty()
    description_selector = db.StringProperty()
    image_selector = db.StringProperty()
    button_selector = db.StringProperty()

    def __init__(self, *args, **kwargs):
        """ Initialize this model """
        super(Buttons, self).__init__(*args, **kwargs)

    def _validate_self(self):
        return True
