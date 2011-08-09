#!/usr/bin/env python
""" 
Name: Email Class
Purpose: All emails from Willet.com will be in this class.
Author:  Barbara Macdonald
Date:  March 2011
"""
import logging
import os

from google.appengine.ext.webapp import template
from google.appengine.api.mail import EmailMessage

from util.consts import *


###################
#### Addresses ####
###################

from_addr = 'z4beth@gmail.com' # must be registered with app engine account

barbara   = 'barbara@getwillet.com'
fraser    = 'fraser.harris@gmail.com'
dev_team  = '%s' % (barbara)
team      = '%s, %s' % (fraser, barbara)

#####################
#### Email Class ####
#####################
class Email():

#### Dev Team Emails ####
    @staticmethod
    def emailBarbara( msg ):
        to_addr = barbara
        subject = '[Willet] Message to Self'
        body    = '<p> %s </p>' % msg
 
        Email.send_email( from_addr, to_addr, subject, body )

    @staticmethod
    def first10Shares( email_addr ):
        subject = '[Willet Referral] We Have Some Results!'
        to_addr =  email_addr
        body    = template.render(os.path.join(os.path.dirname(__file__), 'email_templates/first10.html'), {'campaign_id': campaign_id})
        
        Email.send_email( from_addr, to_addr, subject, body )

    @staticmethod
    def invite( infrom_addr, to_addrs, msg, url, campaign ):
        # TODO(Barbara): Let's be smart about this. We can try to fetch these users 
        # from the db via email and personalize the email.
        to_addr = to_addrs.split(',')
        subject = 'Check This Out!'
        body = template.render(os.path.join(os.path.dirname(__file__), 'email_templates/invite.html'),
            {
                'from_addr' : infrom_addr,
                'msg' : msg,
                'campaign' : campaign
            }
        )
        
        logging.info("Emailing X%sX" % to_addr)
        Email.send_email( from_addr, to_addr, subject, body )

#####################################
#####################################
#####################################
    @staticmethod
    def send_email( from_address, to_address, subject, body ):
        e = EmailMessage(sender=from_address, to=to_address, subject=subject, html=body)
        e.send()
# end class

