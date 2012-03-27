#!/usr/bin/env python
#
# Using MailSnake as MailChimp, from https://github.com/leftium/mailsnake
#
# MailSnake Python wrapper for MailChimp API 1.3
#
# Example:
# >>> from mailsnake import MailSnake
# >>> ms = MailSnake('YOUR MAILCHIMP API KEY')
# >>> ms.ping()
# u "Everything's Chimpy!"
#
# Note:
# API parameters must be passed by name. For example:
# >>> ms.listMemberInfo(id='YOUR LIST ID', email_address='name@email.com')
#
# The MIT License
#
# Copyright (c) 2010 John-Kim Murphy
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

__author__    = 'John-Kim Murphy'
__copyright__ = 'Copyright 2010, John-Kim Murphy'
__credits__   = ['John-Kim Murphy',]
__version__   = '1.3.0.0'

import urllib2
import simplejson as json


class MailChimp(object):
    def __init__(self, apikey = '', extra_params = {}):
        """
            Cache API key and address.
        """
        self.apikey = apikey

        self.default_params = {'apikey':apikey, 'output':'json'}
        self.default_params.update(extra_params)

        dc = 'us1'
        if '-' in self.apikey:
            dc = self.apikey.split('-')[1]
        self.base_api_url = 'https://%s.api.mailchimp.com/1.3/?method=' % dc

    def call(self, method, params = {}):
        url = self.base_api_url + method
        all_params = self.default_params.copy()
        all_params.update(params)

        post_data = urllib2.quote(json.dumps(all_params))
        headers = {'Content-Type': 'application/json'}
        request = urllib2.Request(url, post_data, headers)
        response = urllib2.urlopen(request)

        return json.loads(response.read())

    def __getattr__(self, method_name):
        """ Helper function that maps function calls to API calls

        ie: MailChimp.listSubscribe(...) -> MailChimp.call('listSubscribe',...)
        """
        def get(self, *args, **kwargs):
            params = dict((i,j) for (i,j) in enumerate(args))
            params.update(kwargs)
            return self.call(method_name, params)

        return get.__get__(self)