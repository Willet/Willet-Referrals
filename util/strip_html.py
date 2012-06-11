#!/usr/bin/env python

from HTMLParser import HTMLParser

class MLStripper(HTMLParser):
    def __init__(self):
        self.reset()
        self.fed = []
    def handle_data(self, d):
        self.fed.append(d)
    def get_data(self):
        return ''.join(self.fed)

def strip_html(html=''):
    """This function has known vulnerabilities.

    >>> strip_html('<script><script onload="alert(5);"></script></script>')
    '<script onload="alert(5);">'

    """
    if html is None:
        html = ''

    html = html.replace('&nbsp;', ' ')\
            .replace('<br />', ' ')\
            .replace('<br>', ' ')
    s = MLStripper()
    s.feed(html)
    return s.get_data()