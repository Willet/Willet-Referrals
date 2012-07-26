#!/usr/bin/env python

import datetime
import logging

from apps.app.shopify.models import AppShopify
from apps.email.models import Email
from apps.reengage.models import ReEngage

from util.consts import REROUTE_EMAIL, SHOPIFY_APPS
from util.helpers import generate_uuid


