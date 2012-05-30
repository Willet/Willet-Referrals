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
    def welcomeClient(app_name, to_addr, name, store_name,
                      use_full_name=False):
        to_addr = to_addr
        subject = 'Thanks for Installing "%s"' % (app_name)
        body = ''

        if not use_full_name:
            # Grab first name only
            try:
                name = name.split(' ')[0]
            except:
                pass

        body += "<p>Hi %s,</p>" % (name,)

        if app_name == 'ShopConnection':
            body += """<p>Thanks for installing! Please lets us know if you have any suggestion to improve ShopConnection.</p>"""

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
    def welcomeFraser(app_name, to_addr, name, store_name, store_url,
                      use_full_name=False):
        subject = 'Thanks for Installing "%s"' % (app_name)

        if not app_name:
            logging.warn("Attmpt to email welcome for unknown app %s" % app_name)
            return

        if not use_full_name:
            # Grab first name only
            try:
                name = name.split(' ')[0]
            except:
                pass

        body = """<p>%s</p>
                  <p>Hi %s,</p>
                  <p>We are looking forward to your store launching!  Please lets us know if you have any suggestion to improve %s.</p>
                  <p>Fraser</p>
                  <p>Founder, Willet<br /> www.willetinc.com | Cell 519-580-9876 | <a href='http://twitter.com/fjharris'>@FJHarris</a></p>""" % (store_url, name, app_name)

        Email.send_email(from_address=FRASER,
                         to_address=FRASER,
                         replyto_address=to_addr,
                         subject=subject,
                         body=body,
                         to_name=name)

    @staticmethod
    def goodbyeFromFraser(to_addr, name, app_name):
        to_addr = to_addr
        subject = 'We are sad to see you go :('

        # Grab first name only
        try:
            name = ' %s' % name.split(' ')[0]
        except:
            name = ''

        if 'SIBT' in app_name:
            app_name = "Should I Buy This"
        elif 'Buttons' in app_name:
            app_name = "ShopConnection"

        body = """<p>Hi%s,</p> <p>Sorry to hear things didn't work out with %s.
                  <i>Can you tell us why you uninstalled?</i></p>
                  <p>Thanks,</p>
                  <p>Fraser</p>
                  <p>Founder, Willet<br />
                  www.willetinc.com | Cell 519-580-9876 | <a href="http://twitter.com/fjharris">@FJHarris</a></p> """ % (name, app_name)

        Email.send_email(from_address=FRASER,
                         to_address=to_addr,
                         subject=subject,
                         body=body,
                         to_name=name,
                         replyto_address=FRASER)

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
    def buttons_custom_install_request(app):
        """Mail the dev team about an installation request."""
        client = getattr(app, 'client', None)
        if not client:
            return  # client uninstalled

        subject = 'Buttons Custom Install Request'
        client_addr = getattr(client, 'email')
        client_name = getattr(client, 'name')
        client_domain = getattr(client, 'url', getattr(client, 'domain'))

        msg = '''Client %s <%s> has request a custom Buttons installation.
                 Please go to %s/admin to install the app.''' % (client_name,
                                                                 client_addr,
                                                                 client_domain)
        logging.info(msg)  # lazy boy strikes again
        Email.emailDevTeam(msg=msg,
                           subject=subject,
                           monospaced=False)

    @staticmethod
    def SIBTAsk(client, from_name, from_addr, to_name, to_addr, message,
                vote_url, product=None, products=None, asker_img= None):
        """Please, supply products as their objects.

        Supplying a products list of more than one item will trigger WOSIB
        emails.
        """

        if products is None:
            products = []

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

        try:
            product_img = product.images[0]
        except (TypeError, IndexError), err:
            logging.debug('error while getting product_img: %s' % err,
                          exc_info=True)
            product_img = 'http://rf.rs/static/imgs/blank.png' # blank
        logging.debug('product_img is %r' % product_img)

        if len(products) > 1:  # WOSIB mode
            template_file = 'wosib_ask.html'
        else:
            template_file = 'sibt_ask.html'

        body = template.render(Email.template_path(template_file, client), {
            'URL': URL,
            'from_name': from_name.title(),
            'from_first_name': from_first_name.title(),
            'to_name': to_name.title(),
            'to_first_name': to_first_name.title(),
            'message': message,
            'vote_url': vote_url,
            'asker_img': asker_img,
            'client_name': client.name,
            'client_domain': client.domain,

            # used in WOSIB mode
            'products': products or [None, None],  # just to shut it up

            # used in SIBT mode
            'product_title': getattr(product, 'title', 'Awesome product'),
            'product_img': product_img
        })

        Email.send_email(from_address=FROM_ADDR,
                         to_address=to_addr,
                         to_name=to_name.title(),
                         replyto_address=from_addr,
                         subject=subject,
                         body=body)


    @staticmethod
    def SIBTVoteNotification(instance, vote_type):
        """Send an "A friend Voted!" email to the asker.

        vote_type is a string.
        """
        client = getattr(instance.app_, 'client', None)
        if not client:
            logging.warn('client uninstalled app; '
                         'not emailing on behalf of it.')
            return  # client uninstalled

        if not instance.asker:
            logging.warn('The deuce? Instance has no asker.')
            return  # no need to email anyone

        to_addr = instance.asker.get_attr('email')

        if not to_addr:
            logging.warn('asker has no email; '
                         'not emailing him/her/it.')
            return  # no need to email anyone

        subject = 'A Friend Voted!'
        name = instance.asker.get_full_name() or "Savvy Shopper"

        product_url = "%s#open=1" % instance.url  # full product link
        product_img = instance.product_img

        logging.info("product_url, product_img = %r" % [product_url,
                                                        product_img])

        body = template.render(
            Email.template_path('sibt_voteNotification.html', client),
            {
                'name'          : name.title(),
                'vote_type'     : vote_type,
                'product_url'   : product_url,
                'product_img'   : product_img,
                'client_name'   : client.name,
                'client_domain' : client.domain
            }
        )

        Email.send_email(from_address=FROM_ADDR,
                         to_address=to_addr,
                         subject=subject,
                         body=body)

    @staticmethod
    def SIBTVoteCompletion(instance, product):
        client = getattr(product, 'client', None)
        if not client:
            logging.warn('client uninstalled app; '
                         'not emailing on behalf of it.')
            return  # client uninstalled

        if not instance.asker:
            logging.warn('The deuce? Instance has no asker.')
            return  # no need to email anyone

        to_addr = instance.asker.get_attr('email')
        if not to_addr:
            logging.warn('asker has no email; '
                         'not emailing him/her/it.')
            return  # no need to email anyone

        yesses = instance.get_yesses_count()
        noes = instance.get_nos_count()
        total = (yesses + noes)
        if total == 0:
            buy_it_percentage = 0
        else:
            buy_it_percentage = int(float(float(yesses) / float(total)) * 100)

        buy_it = True if yesses >= noes else False

        name = instance.asker.name or "Savvy Shopper"
        subject = '%s, the votes are in!' % name

        body = template.render(
            Email.template_path('sibt_voteCompletion.html', client), {
                'name': name,
                'product_url': getattr(product, 'resource_url', ''),
                'product_img': product.images[0],
                'yesses': yesses,
                'noes': noes,
                'buy_it': buy_it,
                'buy_it_percentage': buy_it_percentage})

        Email.send_email(from_address=FROM_ADDR,
                         to_address=to_addr,
                         subject=subject,
                         body=body,
                         to_name=name)

    @staticmethod
    def WOSIBAsk(from_name, from_addr, to_name, to_addr, message, vote_url,
                 client, asker_img= None, products=None):
        """Please, supply products as their objects."""
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

        body = template.render(Email.template_path('wosib_ask.html', client),
            {
                'URL'               : URL,
                'from_name'         : from_name.title(),
                'from_first_name'   : from_first_name.title(),
                'to_name'           : to_name.title(),
                'to_first_name'     : to_first_name.title(),
                'message'           : message,
                'vote_url'          : vote_url,
                'asker_img'         : asker_img,
                'client_name'       : client.name,
                'client_domain'     : client.domain,
                'products'          : products or [None, None]  # just to shut it up
            }
        )

        Email.send_email(from_address=FROM_ADDR,
                         to_address=to_addr,
                         to_name=to_name.title(),
                         replyto_address=from_addr,
                         subject=subject,
                         body=body)

    @staticmethod
    def WOSIBVoteNotification(instance, product):
        # similar to SIBTVoteNotification, except because you can't vote 'no',
        # you are just told someone voted on one of your product choices.
        # pass roduct is a Product object.
        client = getattr(instance.app_, 'client', None)
        if not client:
            return  # client uninstalled

        to_addr = instance.asker.get_attr('email')
        if not to_addr:
            return  # no need to email anyone

        subject = 'A Friend Voted!'
        name = instance.asker.get_full_name() or "Savvy Shopper"

        cart_url = "%s#open=1" % instance.link.origin_domain

        body = template.render(Email.template_path('wosib_voteNotification.html',
                                                   client),
                               {'name': name.title(),
                                'cart_url': cart_url,
                                'product': product,
                                'client_name': client.name,
                                'client_domain': client.domain})

        Email.send_email(from_address=FROM_ADDR,
                         to_address=to_addr,
                         subject=subject,
                         body=body,
                         to_name=name)

    ### MAILOUTS ###

    @staticmethod
    def template_path(path, client=None):
        """Returns the email template path for a given client, or the default
        path if the client does not have special templates.
        """
        if client and client.is_vendor:
            vendor_path = os.path.join('apps/email/templates', client.name,
                                       path)
            if os.path.exists(vendor_path):
                return vendor_path
        return os.path.join('apps/email/templates/', path)

    @staticmethod
    def send_email(from_address, to_address, subject, body,
                   to_name= None, replyto_address= None):
        if not replyto_address:
            replyto_address = from_address  # who would reply to "None"?
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