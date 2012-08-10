#!/usr/bin/env python

"""Replacement logging."""

__author__ = 'brian'
__copyright__ = "Copyright 2012, Willet, Inc"

import traceback
import logging as internal_logging

from google.appengine.api import memcache

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

    # tuple of logging methods you can call
    allowed_log_methods = ('debug', 'info', 'warn', 'error', 'critical')

    @classmethod
    def debug(cls, *args, **kwargs):
        """Tallies; does not email."""
        cls._emit(*args, **kwargs)

    @classmethod
    def info(cls, *args, **kwargs):
        """Tallies; does not email."""
        default_dict = {'method': 'info'}
        default_dict.update(kwargs)
        cls._emit(*args, **default_dict)

    @classmethod
    def warn(cls, *args, **kwargs):
        """Tallies; does not email."""
        default_dict = {'method': 'warn'}
        default_dict.update(kwargs)
        cls._emit(*args, **default_dict)

    @classmethod
    def error(cls, *args, **kwargs):
        """Does not send email, unless kwargs[email] = True."""
        default_dict = {'method': 'error', 'include_count': False}
        default_dict.update(kwargs)
        cls._emit(*args, **default_dict)

    @classmethod
    def critical(cls, *args, **kwargs):
        """Does not send email, unless kwargs[email] = False."""
        default_dict = {'method': 'critical', 'email': True,
                        'include_count': False}
        default_dict.update(kwargs)
        cls._emit(*args, **default_dict)

    @classmethod
    def _emit(cls, *args, **kwargs):
        """Emits a {method}-level log.

        Method must be defined in allowed_log_methods.
        Then, if {email} is true, fire off an email with said message.

        If {include_count} is true, message tells you the number of times
        the same error message occurred in the past {MEMCACHE_TIMEOUT} period.
        """
        method = kwargs.get('method', 'debug')
        if not (len(args) and method):
            return  # don't screw with us

        if kwargs.get('include_count', True):  # patch message
            args = list(args)  # first turn immutable tuple into a list
            args[0] = cls._format_msg(args[0])

        log_func = getattr(internal_logging, method, None)
        if not (log_func and method in cls.allowed_log_methods):
            raise AttributeError(u'Method not allowed')

        # fire the logging function.
        log_func(*args)

        # fire off email on live server.
        if kwargs.get('email', False) and not USING_DEV_SERVER:
            # DO NOT use this logging module in emailing scripts! Infinite loops!
            from apps.email.models import Email
            Email.emailDevTeam(args[0], subject='[%s]' % method)

    @classmethod
    def _format_msg(cls, msg=u''):
        """Outputs a string account to the count. If count is 0? No message."""
        count = 0
        try:
            msg2 = msg[msg.find(u':')+1:].strip()
            if msg2:
                count = memcache.incr(msg2, namespace=cls.logs_namespace,
                                     initial_value=0) or 0
        except:
            pass  # no need to try hard

        # remove first 6 items, which are inside middleware
        # remove last 3 items, which are inside logger.py
        # and then reverse the list
        stack = traceback.extract_stack()[6:-3][::-1]
        stack_list = ['%s.%s:%s' % (c[0], c[2], c[1]) for c in stack]
        stack_msg = '\n> '.join(stack_list)

        msg = '%s\n\nTraceback (most recent call last):\n%s' % (msg, stack_msg)

        if count:
            msg = u"%s\n\n(logged %d times in the past %d secs)" % (
                msg, count, memcache.get_stats().get('oldest_item_age', 0))
        return msg