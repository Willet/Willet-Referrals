#!/usr/bin/env python

"""Replacement logging."""

__author__ = 'brian'
__copyright__ = "Copyright 2012, Willet, Inc"

import logging as internal_logging

from google.appengine.api import memcache

# DO NOT use this logging module in emailing scripts! Infinite loops!
from apps.email.models import Email

from util.consts import USING_DEV_SERVER


class logging(object):
    """Drop-in replacement for the internal logging module.

    Use it like the original logging module.

    Several behaviours are patched to improve logging experience.
    - info, warn, error and critical messages all display trace stack
      by default.
    - info and warn messages will include the number of times the same
      error message occurred in the past {MEMCACHE_TIMEOUT} period.
    - error-level messages will cause alert emails to be sent to
      addresses listed in ADMIN_EMAILS if the message as an 'email' kwarg.
    - critical-level  messages will cause alert emails to be sent to
      addresses listed in ADMIN_EMAILS unless kwarg[email] is set to False.

    TODO: control email behaviour via memcache variable
    TODO: auto-raise alert level if too many messages of the same text appear
    """
    logs_namespace = 'logging'  # to avoid interference with memcache items

    @classmethod
    def debug(cls, *args, **kwargs):
        if not len(args):
            return  # don't screw with us

        count = cls._get_tally(msg=args[0])

        args = list(args)  # turn immutable tuple into a list
        args[0] = u"%s%s" % (args[0], cls._format_msg(count))

        kwargs['exc_info'] = True
        internal_logging.debug(*args, **kwargs)

    @classmethod
    def info(cls, *args, **kwargs):
        if not len(args):
            return  # don't screw with us

        count = cls._get_tally(msg=args[0])

        args = list(args)  # turn immutable tuple into a list
        args[0] = u"%s%s" % (args[0], cls._format_msg(count))

        kwargs['exc_info'] = True
        internal_logging.info(*args, **kwargs)

    @classmethod
    def warn(cls, *args, **kwargs):
        if not len(args):
            return  # don't screw with us

        count = cls._get_tally(msg=args[0])

        args = list(args)  # turn immutable tuple into a list
        args[0] = u"%s%s" % (args[0], cls._format_msg(count))
        kwargs['exc_info'] = True
        internal_logging.warn(*args, **kwargs)

    @classmethod
    def error(cls, *args, **kwargs):
        """Does not send email, unless kwargs[email] = True."""
        if not len(args):
            return  # don't screw with us

        kwargs['exc_info'] = True
        internal_logging.error(*args, **kwargs)
        if not USING_DEV_SERVER and kwargs.get('email', False):
            Email.emailDevTeam(args[0], subject='[Error]')

    @classmethod
    def critical(cls, *args, **kwargs):
        """Can you even issue a critical message?"""
        if not len(args):
            return  # don't screw with us

        kwargs['exc_info'] = True
        internal_logging.critical(*args, **kwargs)
        if not USING_DEV_SERVER and kwargs.get('email', True):
            Email.emailDevTeam(args[0], subject='[CRITICAL]')

    @classmethod
    def _format_msg(cls, count=0):
        """Outputs a string account to the count. If count is 0? No message."""
        if count:
            return u"\n\nThis message showed %d times in the past %d seconds." % (
                count, memcache.get_stats().get('oldest_item_age', 0))
        return u''

    @classmethod
    def _get_tally(cls, msg=None):
        """Count the number of times a similar message appeared.

        Because logs usually come in the form
        {Problem}: {Description}
        e.g. Cannot set memcache: Brian is a n00b
        _get_tally tallies tallies only using the part before the messages'
        first colon.

        Returns: the count (as far as memcache can tell)
        """
        try:
            msg = msg[msg.find(':')+1:].strip()
            if msg:
                return memcache.incr(msg, namespace=cls.logs_namespace,
                                     initial_value=0) or 0
        except:
            pass  # no need to try hard
        return 0