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
matt      = 'harrismc@gmail.com'
dev_team  = '%s, %s' % (barbara, matt)
team      = '%s, %s' % (fraser, barbara)

#####################
#### Email Class ####
#####################
class Email():

#### Dev Team Emails ####
    @staticmethod
    def emailBarbara(msg):
        to_addr = dev_team #barbara
        subject = '[Willet]'
        body    = '<p> %s </p>' % msg
 
        logging.info("Emailing Barbara")
        Email.send_email(from_addr, to_addr, subject, body)

    @staticmethod
    def first10Shares(email_addr):
        subject = '[Willet Referral] We Have Some Results!'
        to_addr =  email_addr
        body    = template.render(Email.template_path('first10.html'), {
            'campaign_id': campaign_id
        })
        
        Email.send_email(from_addr, to_addr, subject, body)

    @staticmethod
    def invite(infrom_addr, to_addrs, msg, url, app):
        # TODO(Barbara): Let's be smart about this. We can try to fetch these users 
        # from the db via email and personalize the email.
        to_addr = to_addrs.split(',')
        subject = 'I\'ve Given You A Gift!'
        body = template.render(Email.template_path('invite.html'),
            {
                'from_addr' : infrom_addr,
                'msg' : msg,
                'app' : app 
            }
        )
        
        logging.info("Emailing X%sX" % to_addr)
        Email.send_email(from_addr, to_addr, subject, body)

    @staticmethod
    def SIBTVoteNotification( to_addr, name, vote_type, vote_url, product_img ):
        to_addr = to_addr
        subject = 'A Friend Voted!'
        if name == "":
            name = "Savvy Shopper"
        body = template.render(Email.template_path('sibt_voteNotification.html'),
            {
                'name'        : name,
                'vote_type'   : vote_type,
                'vote_url'    : vote_url,
                'product_img' :  product_img
            }
        )
        
        logging.info("Emailing X%sX" % to_addr)
        Email.send_email(from_addr, to_addr, subject, body)

    @staticmethod 
    def template_path(path):
        return os.path.join('apps/email/templates/', path)

    @staticmethod
    def send_email(from_address, to_address, subject, body):
        e = EmailMessage(
            sender=from_address, 
            to=to_address, 
            subject=subject, 
            html=body
        )
        e.send()
# end class

