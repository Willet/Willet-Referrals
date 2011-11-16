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

def strip_html(html):
    html = html.replace('&nbsp;', ' ')\
            .replace('<br />', ' ')\
            .replace('<br>', ' ')
    s = MLStripper()
    s.feed(html)
    return s.get_data()

