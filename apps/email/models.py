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


barbara   = 'barbara@getwillet.com'
fraser    = 'fraser.harris@gmail.com'
matt      = 'harrismc@gmail.com'
dev_team  = '%s, %s, %s' % (fraser, barbara, matt)
team      = '%s, %s' % (fraser, barbara)

from_addr = barbara

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
    def welcomeClient( app_name, to_addr, name, store_name ):
        to_addr = to_addr
        subject = 'Thanks for Installing "%s"' % (app_name)
        body = """<p>Hi %s,</p> <p>Thanks for installing "%s"!  We are really excited to work with you and your customers.  We look forward to seeing your customers benefit from getting advice from their friends and your store, %s, getting the exposure it deserves!</p> <p>You may notice small changes in the look and feel of the app in the coming weeks.  We are constantly making improvements to increase the benefit to you!</p> <p>Our request is that you let us know your ideas, comments, concerns or challenges! I can promise we will listen and respond to each and every one.</p> <p>Welcome aboard,</p> <p>Cheers,</p> <p>Fraser</p> <p>Founder, Willet<br /> www.willetinc.com<br /> Cell 519-580-9876<br /> @fjharris</p> """ % (name, app_name, store_name)
        
        logging.info("Emailing X%sX" % to_addr)
        Email.send_email(fraser, to_addr, subject, body)


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
    def SIBTVoteCompletion(to_addr, name, product_url, product_img, yesses, noes):
        if name == "":
            name = "Savvy Shopper"
        subject = '%s the votes are in!' % name
        total = (yesses + noes)
        if total == 0:
            buy_it_percentage = 0
        else:
            buy_it_percentage = int(float( float(yesses) / float(total) ) * 100)

        if yesses > noes:
            buy_it = True
        else:
            buy_it = False

        body = template.render(
            Email.template_path('sibt_voteCompletion.html'), {
                'name': name,
                'product_url': product_url,
                'product_img': product_img,
                'yesses': yesses,
                'noes': noes,
                'buy_it': buy_it,
                'buy_it_percentage': buy_it_percentage
        })

        logging.info("Emailing X%sX" % to_addr)
        Email.send_email(from_addr, to_addr, subject, body)

    @staticmethod 
    def template_path(path):
        return os.path.join('apps/email/templates/', path)

    @staticmethod
    def send_email(from_address, to_address, subject, body):
        try:
            e = EmailMessage(
                    sender=from_address, 
                    to=to_address, 
                    subject=subject, 
                    html=body
                    )
            e.send()
        except Exception,e:
            logging.error('error sending email: %s', e)

# end class

