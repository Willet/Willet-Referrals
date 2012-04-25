#!/usr/bin/env python
""" 
Name: Email Class
Purpose: All emails from Willet.com will be in this class.
Author:  Barbara Macdonald
Date:  March 2011
"""
import logging
import os

from google.appengine.api import taskqueue
from google.appengine.api.app_identity import get_application_id
from google.appengine.ext.webapp import template

from util.consts import *
from util.helpers import url 

INFO = "info@getwillet.com"
FRASER = 'fraser@getwillet.com'
BRIAN = "brian@getwillet.com"
NICK = 'nick@getwillet.com'

DEV_TEAM = '%s, %s, %s' % (FRASER, NICK, BRIAN)
FROM_ADDR = INFO

DEV_APPS = {
    # see above for key names
    INFO: [],
    FRASER: ['fraser-willet','fraser-willet2'],
    BRIAN: ['brian-willet', 'brian-willet2', 'brian-willet3', 'brian-willet4'],
    NICK: ['willet-nterwoord'],
    
    DEV_TEAM: [APP_LIVE] # email everyone if on live server
}

class Email():
    """ All email methods are held in this class.  All emails are routed
        through Email.send_email.  Here we control our email provider.
        Currently: SendGrid for single recipients, App Engine for multiple recipients
    """
    @staticmethod
    def emailDevTeam(msg, subject=None, monospaced=False):
        ''' If on a dev site, this function will only email its site owner (see DEV_APPS). '''
        to_addrs = []
        if subject is None:
            subject = '[Willet]'

        if monospaced is True:
            body = '<pre>%s</pre>' % msg
        else:
            body = '<p>%s</p>' % msg
        
        appname = get_application_id()
        to_addrs = [dev_member for dev_member in DEV_APPS if appname in DEV_APPS[dev_member]]
        
        if to_addrs:
            Email.send_email(from_address=FROM_ADDR,
                             to_address=','.join(to_addrs),
                             subject=subject,
                             body=body,
                             to_name='Dev Team')

    @staticmethod
    def welcomeClient(app_name, to_addr, name, store_name):
        to_addr = to_addr
        subject = 'Thanks for Installing "%s"' % (app_name)
        body = ''
    
        # Grab first name only
        try:
            name = name.split(' ')[0]
        except:
            pass

        body += "<p>Hi %s,</p>" % (name,)

        if app_name == 'ShopConnection':
            body += """<p>Thanks for installing %s!  We are excited to see your store, %s, getting the exposure it deserves.</p>
                  <p>Our <a href='http://willetshopconnection.blogspot.com/2012/03/customization-guide-to-shopconnection.html'>Customization Guide</a> can help you modify the buttons to better suit your store.</p>
                  <p>If you have any ideas on how to improve %s, please let us know.</p>""" % (app_name, store_name, app_name)
        
        elif app_name == 'Should I Buy This':
            body += """<p>Thanks for installing %s!  We are excited to see your store, %s, getting the exposure it deserves.</p>
                  <p>You may notice small changes in the look and feel of the app in the coming weeks.  We are constantly making improvements to increase the benefit to you!</p>
                  <p>If you have any ideas on how to improve %s, please let us know.</p>""" % (app_name, store_name, app_name)

        else:
            logging.warn("Attmpt to email welcome for unknown app %s" % app_name)
            return

        body += """<p>Fraser</p>
                <p>Founder, Willet<br /> www.willetinc.com | Cell 519-580-9876 | <a href="http://twitter.com/fjharris">@FJHarris</a></p>"""

        Email.send_email(from_address=FRASER,
                         to_address=to_addr,
                         subject=subject,
                         body=body,
                         to_name=name)

    @staticmethod
    def goodbyeFromFraser(to_addr, name, app_name):
        to_addr = to_addr
        subject = 'We are sad to see you go :('
        
        # Grab first name only
        try:
            name = name.split(' ')[0]
        except:
            pass

        if 'SIBT' in app_name:
            app_name = "Should I Buy This"
        elif 'Buttons' in app_name:
            app_name = "ShopConnection"
        elif 'WOSIB' in app_name:
            return

        body = """<p>Hi %s,</p> <p>Sorry to hear things didn't work out with %s.
                  <i>Can you tell us why you uninstalled?</i></p>
                  <p>Thanks,</p>
                  <p>Fraser</p>
                  <p>Founder, Willet<br />
                  www.willetinc.com | Cell 519-580-9876 | <a href="http://twitter.com/fjharris">@FJHarris</a></p> """ % (name, app_name)
        
        Email.send_email(from_address=FRASER,
                         to_address=to_addr,
                         subject=subject,
                         body=body,
                         to_name=name)

    @staticmethod
    def report_smart_buttons(email="info@getwillet.com", items={},
                             networks={}, shop_name=None, client_name=None):
        if shop_name is None:
            shop_name = ""

        if client_name is None:
            client_name = ""

        body = template.render(
            Email.template_path('smart_buttons_report.html'),
            {
                'willet_url'    : URL,
                'shop_name'     : shop_name,
                'client_name'   : client_name,
                'item_shares'   : items,
                'network_shares': networks
            }
        )

        subject = "Weekly Smart Buttons Report"

        Email.send_email(from_address=FROM_ADDR,
                         to_address=email,
                         to_name=client_name.title(),
                         subject=subject,
                         body=body)
    
    @staticmethod
    def SIBTAsk(from_name, from_addr, to_name, to_addr, message, vote_url,
                product_img, product_title, client_name, client_domain,
                asker_img= None):
        subject = "Can I get your advice?"
        to_first_name = from_first_name = ''

        # Grab first name only
        try:
            from_first_name = from_name.split(' ')[0]
        except:
            from_first_name = from_name
        try:
            to_first_name = to_name.split(' ')[0]
        except:
            to_first_name = to_name
        
        body = template.render(Email.template_path('sibt_ask.html'),
            {
                'from_name'         : from_name.title(),
                'from_first_name'   : from_first_name.title(),
                'to_name'           : to_name.title(),
                'to_first_name'     : to_first_name.title(),
                'message'           : message,
                'vote_url'          : vote_url,
                'product_title'     : product_title,
                'product_img'       : product_img,
                'asker_img'         : asker_img,
                'client_name'       : client_name,
                'client_domain'     : client_domain
            }
        )
        
        Email.send_email(from_address=FROM_ADDR,
                         to_address=to_addr,
                         to_name=to_name.title(),
                         replyto_address=from_addr,
                         subject=subject,
                         body=body)

    @staticmethod
    def SIBTVoteNotification(to_addr, name, vote_type, product_url, product_img, client_name, client_domain):
        to_addr = to_addr
        subject = 'A Friend Voted!'
        if name == "":
            name = "Savvy Shopper"
        body = template.render(Email.template_path('sibt_voteNotification.html'),
            {
                'name'          : name.title(),
                'vote_type'     : vote_type,
                'product_url'   : product_url,
                'product_img'   : product_img,
                'client_name'   : client_name,
                'client_domain' : client_domain 
            }
        )
        
        Email.send_email(from_address=FROM_ADDR,
                         to_address=to_addr,
                         subject=subject,
                         body=body)

    @staticmethod
    def SIBTVoteCompletion(to_addr, name, product_url, product_img, yesses, noes):
        if name == "":
            name = "Savvy Shopper"
        subject = '%s the votes are in!' % name
        total = (yesses + noes)
        if total == 0:
            buy_it_percentage = 0
        else:
            buy_it_percentage = int(float(float(yesses) / float(total)) * 100)

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

        Email.send_email(from_address=FROM_ADDR,
                         to_address=to_addr,
                         subject=subject,
                         body=body,
                         to_name=name)

    @staticmethod
    def WOSIBAsk(from_name, from_addr, to_name, to_addr, message, vote_url,
                 client_name, client_domain, asker_img= None):
        subject = "Which one should I buy?"
        to_first_name = from_first_name = ''

        # Grab first name only
        try:
            from_first_name = from_name.split(' ')[0]
        except:
            from_first_name = from_name
        try:
            to_first_name = to_name.split(' ')[0]
        except:
            to_first_name = to_name
        
        body = template.render(Email.template_path('wosib_ask.html'),
            {
                'from_name'         : from_name.title(),
                'from_first_name'   : from_first_name.title(),
                'to_name'           : to_name.title(),
                'to_first_name'     : to_first_name.title(),
                'message'           : message,
                'vote_url'          : vote_url,
                'asker_img'         : asker_img,
                'client_name'       : client_name,
                'client_domain'     : client_domain
            }
        )
        
        Email.send_email(from_address=FROM_ADDR,
                         to_address=to_addr,
                         to_name=to_name.title(),
                         replyto_address=from_addr,
                         subject=subject,
                         body=body)

    @staticmethod
    def WOSIBVoteNotification(to_addr, name, cart_url, client_name, client_domain):
        # similar to SIBTVoteNotification, except because you can't vote 'no',
        # you are just told someone voted on one of your product choices.
        to_addr = to_addr
        subject = 'A Friend Voted!'
        if name == "":
            name = "Savvy Shopper"
        body = template.render(Email.template_path('wosib_voteNotification.html'),
            {
                'name'        : name.title(),
                'cart_url'    : cart_url,
                'client_name' : client_name,
                'client_domain' : client_domain 
            }
        )
        
        logging.info("Emailing '%s'" % to_addr)
        Email.send_email(from_address=FROM_ADDR,
                         to_address=to_addr,
                         subject=subject,
                         body=body,
                         to_name=name)
    
    @staticmethod
    def WOSIBVoteCompletion(to_addr, name, products):
        if name == "":
            name = "Savvy Shopper"
        subject = '%s, the votes are in!' % name
        
        # would have been much more elegant had django 0.96 gotten the 
        # {% if array|length > 1 %} notation (it doesn't work in GAE)
        product = products[0]
        if len (products) == 1:
            products = False
        
        body = template.render(
            Email.template_path('wosib_voteCompletion.html'), {
                'name': name,
                'products': products,
                'product' : product
        })

        logging.info("Emailing '%s'" % to_addr)
        Email.send_email(from_address=FROM_ADDR,
                         to_address=to_addr,
                         subject=subject,
                         body=body,
                         to_name=name)

    ### MAILOUTS ###

    @staticmethod 
    def template_path(path):
        return os.path.join('apps/email/templates/', path)

    @staticmethod
    def send_email(from_address, to_address, subject, body,
                   to_name= None, replyto_address= None):
        taskqueue.add(
                url=url('SendEmailAsync'),
                params={
                    'from_address': from_address,
                    'to_address': to_address,
                    'subject': subject,
                    'body': body,
                    'to_name': to_name,
                    'replyto_address': replyto_address
                }
            )
# end class
