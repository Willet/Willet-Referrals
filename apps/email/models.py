#!/usr/bin/env python
""" 
Name: Email Class
Purpose: All emails from Willet.com will be in this class.
Author:  Barbara Macdonald
Date:  March 2011
"""
import logging
import os
import urllib, urllib2

from django.utils import simplejson as json
from google.appengine.api import urlfetch
from google.appengine.api.mail import EmailMessage
from google.appengine.ext.webapp import template

from util.consts import *

###################
#### Addresses ####
###################

info = "info@getwillet.com"

barbara   = "barbara@getwillet.com"
fraser    = 'fraser@getwillet.com'
matt      = 'harrismc@gmail.com'
dev_team  = '%s, %s, %s' % (fraser, barbara, matt)
team      = '%s, %s' % (fraser, barbara)

from_addr = 'z4beth@gmail.com' #barbara

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
    
        # Grab first name only
        try:
            name = name.split(' ')[0]
        except:
            pass

        body = """<p>Hi %s,</p> <p>Thanks for installing "%s"!  We are really excited to work with you and your customers.  We look forward to seeing your customers benefit from getting advice from their friends and your store, %s, getting the exposure it deserves!</p> <p>You may notice small changes in the look and feel of the app in the coming weeks.  We are constantly making improvements to increase the benefit to you!</p> <p>Our request is that you let us know your ideas, comments, concerns or challenges! I can promise we will listen and respond to each and every one.</p> <p>Welcome aboard,</p> <p>Cheers,</p> <p>Fraser</p> <p>Founder, Willet<br /> www.willetinc.com | Cell 519-580-9876 | <a href="http://twitter.com/fjharris">@FJHarris</a></p>""" % (name, app_name, store_name)
        
        logging.info("Emailing X%sX" % to_addr)
        Email.send_email(fraser, to_addr, subject, body)

    @staticmethod
    def goodbyeFromFraser( to_addr, name, app_name ):
        to_addr = to_addr
        subject = 'We are sad to see you go :('
    
        # Grab first name only
        try:
            name = name.split(' ')[0]
        except:
            pass

        if 'SIBT' in app_name:
            app_name = "Should I Buy This"
        else:
            app_name = "ShopConnection"

        body = """<p>Hi %s,</p> <p>Sorry to hear things didn't work out with "%s", but I appreciate you giving it a try.</p> <p>If you have any suggestions, comments or concerns about the app, please let me know.</p> <p>Best,</p> <p>Fraser</p> <p>Founder, Willet<br /> www.willetinc.com | Cell 519-580-9876 | <a href="http://twitter.com/fjharris">@FJHarris</a></p> """ % (name, app_name)
        
        logging.info("Emailing X%sX" % to_addr)
        Email.send_email(fraser, to_addr, subject, body)

    @staticmethod
    def SIBTVoteNotification( to_addr, name, vote_type, vote_url, product_img, client_name, client_domain ):
        to_addr = to_addr
        subject = 'A Friend Voted!'
        if name == "":
            name = "Savvy Shopper"
        body = template.render(Email.template_path('sibt_voteNotification.html'),
            {
                'name'        : name.title(),
                'vote_type'   : vote_type,
                'vote_url'    : vote_url,
                'product_img' : product_img,
                'client_name' : client_name,
                'client_domain' : client_domain 
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

    ### MAILOUTS ###
    @staticmethod
    def Mailout_Nov28(to_addr, name, app_uuid):
        subject = 'Updates About "Should I Buy This"!'
        body = template.render(
            Email.template_path('mailout_nov28.html'), {
                'name': name,
                'app_uuid' : app_uuid
        })

        logging.info("Emailing X%sX" % to_addr)
        Email.send_email(from_addr, to_addr, subject, body)

    @staticmethod 
    def template_path(path):
        return os.path.join('apps/email/templates/', path)

    @staticmethod
    def send_email(from_address, to_address, subject, body):
        if ',' in to_address:
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
        else:
            params = {
                "api_user" : "BarbaraEMac",
                "api_key"  : "w1llet!!",
                "to"       : to_address,
                "subject"  : subject,
                "html"     : body,
                "from"     : info,
                "fromname" : "Willet",
                "bcc"      : barbara
            }

            #logging.info('https://sendgrid.com/api/mail.send.json?api_key=w1llet!!&%s' % payload)

            result = urlfetch.fetch(
                url     = 'https://sendgrid.com/api/mail.send.json',
                payload = urllib.urlencode( params ), 
                method  = urlfetch.POST,
                headers = {'Content-Type': 'application/x-www-form-urlencoded'}
            )
            logging.info("%s"% result.content)
# end class

