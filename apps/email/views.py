#!/usr/bin/env python

__author__      = "Willet Inc."
__copyright__   = "Copyright 2012, The Willet Corporation"

import logging

from apps.email.models             import Email
from apps.app.models               import *
from apps.sibt.shopify.models      import *
from apps.user.models              import *

from util.urihandler       import URIHandler

class EmailEveryone (URIHandler):
    """ Task Queue-based blast email URL. """

    def get (self):
        # render the mail client
        template_values = {}
        self.response.out.write(self.render_page('mass_mail_client.html', template_values))

    def post( self ):
        logging.info("Sending everyone an email.")
        
        target_version = self.request.get('version', '3')
        logging.info ('target_version = %r' % target_version)
        
        all_sibts = SIBTShopify.all().fetch(1000000)
        logging.info ('all_sibts = %r' % all_sibts)

        try:
            assert (len (self.request.get('subject')) > 0)
            assert (len (self.request.get('body')) > 0)
        except:
            self.error(400) # Bad Request
            return

        all_emails = []
        # no try-catches in list comprehension... so this.
        for sibt in all_sibts:
            try:
                assert (hasattr (sibt, 'client'))       # lagging cache
                assert (hasattr (sibt.client, 'email')) # bad install
                
                # construct email
                body = template.render(Email.template_path('general_mail.html'),
                    {
                        'title'        : self.request.get('subject'),
                        'content'      : self.request.get('body')
                    }
                )
                
                if sibt.version == target_version: # testing
                    email = {
                        'client': sibt.client,
                        # 'from': ...
                        'to': sibt.client.email,
                        'subject': self.request.get('subject'),
                        'body': body
                    }
                    all_emails.append (email)
                    logging.info('added %r to all_emails' % sibt.client)
            except Exception, e:
                logging.error ("can't find client/email for app: %r; %s" % (sibt, e), exc_info = True)
                pass # miss a client!

        for email in all_emails:
            taskqueue.add ( # have them sent one by one.
                url = url ('EmailSomeone'),
                params = email
            )
        
        self.response.headers['Content-Type'] = 'text/plain'
        self.response.out.write ("%r" % all_emails)
        return

class EmailSomeone (URIHandler):
    def get (self):
        self.post() # yup, taskqueues are randomly GET or POST.

    def post( self ):
        try:
            Email.send_email (
                self.request.get('from', 'fraser@getwillet.com'),
                self.request.get('to'),
                self.request.get('subject'),
                self.request.get('body'),
                self.request.get('to_name', None),
                self.request.get('reply-to', None)
            )
            self.response.out.write ("200 OK")
        except Exception, e:
            logging.error ("Error sending one of the emails in batch! %s\n%r" % 
                (e, [
                    self.request.get('from', 'fraser@getwillet.com'),
                    self.request.get('to'),
                    self.request.get('subject'),
                    self.request.get('body'),
                    self.request.get('to_name', None),
                    self.request.get('reply-to', None)
                ]), exc_info = True
            )
