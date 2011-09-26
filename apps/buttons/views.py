#!/usr/bin/env python

from util.urihandler import URIHandler

class ButtonLoader(URIHandler):
    def get(self):
        # dyncamic loader for buttons
        # this will return js

class EditButtonAjax(URIHandler):
    def post(self, button_id):
        # handle posting from the edit form
        pass

class EditButton(URIHandler):
    def get(self, button_id):
        # show the edit form
        pass

class ListButtons(URIHandler):
    def get(self):
        # show the buttons enabled for this site
        client = self.get_client()
        if client:
            shop_owner = client.merchant.get_attr('full_name')
        else:
            shop_owner = 'Awesomer Bob'

        template_values = {
            'query_string': self.request.query_string,
            'shop_owner': shop_owner 
        }
        
        self.response.out.write(self.render_page('list.html', template_values))

