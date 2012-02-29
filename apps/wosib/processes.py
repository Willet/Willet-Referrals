#!/usr/bin/env python

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2012, Willet, Inc"

import hashlib
import random
import re

from datetime import datetime
from django.utils import simplejson as json
from google.appengine.api import taskqueue
from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import template 
from google.appengine.ext.webapp.util import run_wsgi_app

from apps.action.models       import UserAction
from apps.app.models          import App
from apps.app.models          import get_app_by_id
from apps.email.models        import Email
from apps.link.models         import Link
from apps.product.shopify.models import ProductShopify
from apps.product.models      import Product
from apps.user.models         import User
from apps.user.actions        import UserIsFBLoggedIn
from apps.user.models         import User
from apps.user.models         import get_or_create_user_by_cookie
from apps.user.models         import get_user_by_cookie
from apps.user.models         import get_or_create_user_by_cookie
from apps.wosib.actions       import *
from apps.wosib.models        import WOSIBInstance
from apps.wosib.models        import PartialWOSIBInstance

from util.consts              import *
from util.helpers             import remove_html_tags
from util.helpers             import url 
from util.strip_html          import strip_html
from util.urihandler          import URIHandler


class DoWOSIBVote(URIHandler):
    def post(self):
        # since WOSIBInstances contain more than one product, clients
        # just call DoWOSIBVote multiple time to vote on each product
        # they select. (right now, the UI permits selection of only 
        # product per vote anyway)
        instance_uuid = self.request.get('instance_uuid')
        logging.info ("instance_uuid = %s" % instance_uuid)
        product_uuid = self.request.get('product_uuid')
        
        instance = WOSIBInstance.get(instance_uuid)
        app = instance.app_
        user = get_or_create_user_by_cookie(self, app)

        # Make a Vote action for this User
        action = WOSIBVoteAction.create(user, instance, product_uuid)
        instance.increment_votes () # increase instance vote counter
        instance.put()

        # Tell the Asker they got a vote!
        email = instance.asker.get_attr('email')
        if email != "":
            Email.WOSIBVoteNotification(
                email, 
                instance.asker.get_full_name(), 
                instance.link.origin_domain, # cart url
                app.client.name,
                app.client.domain
        )

        # client just cares if it was HTTP 200 or 500.
        self.response.out.write('ok')

class GetExpiredWOSIBInstances(URIHandler):
    def post(self):
        return self.get()
    
    def get(self):
        """Gets a list of WOSIB instances to be expired and emails to be sent"""
        right_now = datetime.datetime.now()
        expired_instances = WOSIBInstance.all()\
                .filter('is_live =', True)\
                .filter('end_datetime <=', right_now) 

        for instance in expired_instances:
            taskqueue.add(
                url = url('RemoveExpiredWOSIBInstance'),
                params = {
                    'instance_uuid': instance.uuid    
                }
            )
        logging.info('expiring %d instances' % expired_instances.count())

class RemoveExpiredWOSIBInstance(webapp.RequestHandler):
    def post(self):
        return self.get()
    
    def get(self):
        """Updates the WOSIB instance in a transaction and then emails the user"""
        def txn(instance):
            instance.is_live = False
            instance.put()
            return instance
        
        instance = WOSIBInstance.get(self.request.get('instance_uuid'))
        if instance != None:
            result_instance = db.run_in_transaction(txn, instance)
            email = instance.asker.get_attr('email')
            if email != "":
                Email.WOSIBVoteCompletion(
                    email,
                    result_instance.asker.get_full_name(),
                    result_instance.get_winning_products()
                )
        else:
            logging.error("could not get instance for uuid %s" % instance_uuid)
        logging.info('done expiring')

class TrackWOSIBShowAction(URIHandler):
    def get(self):
        """Compatibility with iframe shizz"""
        self.post()

    def post(self):
        """So javascript can track a wosib specific show actions"""
        success = False
        instance = app = user = action = None
        if self.request.get('instance_uuid'):
            instance = WOSIBInstance.get(self.request.get('instance_uuid')) 
        if self.request.get('app_uuid'):
            app = App.get(self.request.get('app_uuid')) 
        if self.request.get('user_uuid'):
            user = User.get(self.request.get('user_uuid')) 

        what = self.request.get('evnt')
        url = self.request.get('refer_url')
        if not url:
            # WOSIB doesn't have a target URL, but if refer is missing and target exists, use it
            url = self.request.get('target_url')

        try:
            logging.debug ('TrackWOSIBShowAction: user = %s, instance = %s, what = %s' % (user, instance, what))
            action_class = globals()[what]
            action = action_class.create(user, 
                    instance = instance, 
                    url = url,
                    app = app,
            )
        except Exception,e:
            logging.warn('(this is not serious) could not create class: %s' % e)
            try:
                logging.debug ('TrackWOSIBShowAction 2: user = %s, instance = %s, what = %s' % (user, instance, what))
                action = WOSIBShowAction.create(user, instance, what)
            except Exception, e:
                logging.error('this is serious: %s' % e, exc_info=True)
            else:
                logging.info('tracked action: %s' % action)
                success = True
        else:
            logging.info('tracked action: %s' % action)
            success = True

        self.response.out.write('')

class TrackWOSIBUserAction(URIHandler):
    """ For actions WITH AN INSTANCE """
    def get(self):
        """Compatibility with iframe shizz"""
        self.post()

    def post(self):
        """So javascript can track a wosib specific show actions"""
        success = False
        instance = app = user = action = None
        if self.request.get('instance_uuid'):
            instance = WOSIBInstance.get(self.request.get('instance_uuid')) 
        if self.request.get('app_uuid'):
            app = App.get(self.request.get('app_uuid'))
        if self.request.get('user_uuid'):
            user = User.get(self.request.get('user_uuid'))
        what = self.request.get('what')
        url = self.request.get('target_url')

        action = None
        try:
            action_class = globals()[what]
            action = action_class.create(user, 
                    instance = instance, 
                    url = url,
                    app = app,
            )
        except Exception,e:
            logging.warn('(this is not serious) could not create class: %s' % e)
            try:
                action = WOSIBUserAction.create(user, instance, what)
            except Exception, e:
                logging.error('this is serious: %s' % e, exc_info=True)
            else:
                logging.info('tracked action: %s' % action)
                success = True
        else:
            logging.info('tracked action: %s' % action)
            success = True

        self.response.out.write('')

class StartPartialWOSIBInstance( URIHandler ):
    def get (self):
        self.post()
    
    def post( self ):
        app     = App.get( self.request.get( 'app_uuid' ) )
        link    = Link.get_by_code( self.request.get( 'willt_code' ) )
        
        products = self.request.get( 'product_uuids' )
        logging.info ('products = %s' % products)
        user    = User.get( self.request.get( 'user_uuid' ) )
        PartialWOSIBInstance.create( user, app, link, products.split(',') )

class StartWOSIBInstance(URIHandler):
    def post(self):
        app  = App.get (self.request.get('app_uuid'))
        link = Link.get_by_code(self.request.get('willt_code')) # this is crazy
        products = self.request.get( 'product_uuids' )
        logging.info ('products = %s' % products)
        user    = User.get( self.request.get( 'user_uuid' ) )

        logging.info("Starting WOSIB instance for %s" % link.target_url )

        # defaults
        response = {
            'success': False,
            'data': {
                'instance_uuid': None,
                'message': None
            }
        }

        try:
            # Make the Instance! "None" sets vote time to 6 hrs
            instance = app.create_instance(user, None, link)
        
            response['success'] = True
            response['data']['instance_uuid'] = instance.uuid
        except Exception,e:
            response['data']['message'] = str(e)
            logging.error('we had an error creating the instnace', exc_info=True)

        self.response.out.write(json.dumps(response))

class StartWOSIBAnalytics(URIHandler):
    # StartWOSIBAnalytics will eventually serve the same purpose as StartSIBTAnalytics
    # in SIBT: tally WOSIB actions.
    def get(self):
        # TODO: WOSIB Analytics
        self.response.out.write("No analytics yet")


class SendWOSIBFriendAsks( URIHandler ):
    """ Sends messages to email & FB friends 

    Expected inputs:
        friends: JSON-encoded <Array> [ <array> [ <string> type, <string> name, <string> identifier ]
        asker: JSON-encoded <array> [<string> name, <string> email_address [, <string> picture_url ]]
        msg: <string> message
        default_msg: <string> message before user edited it
        app_uuid: <string> a WOSIB app uuid
        willt_code: <string> willt_code corresponding to a parital WOSIB instance
        user_uuid: <string> a <User> uuid
        fb_access_token: <string> a Facebook API access token for this user
        fb_id: <string> a Facebook user id for this user
    
    Expected output (JSON-encoded):
        success: <Boolean> at least some friends were successfully contacted
        data: <Dict>
            message: <String> description of outcome
            warnings: <Array> [ <string> explanation of any incompleted friend asks ] 
    """
    def get (self):
        self.post()
    
    def post( self ):
        logging.info("TARGETTED_SHARE_WOSIB_EMAIL_AND_FB")
        
        # Fetch arguments 
        friends     = json.loads( self.request.get('friends') )
        asker       = json.loads( self.request.get('asker') )
        msg         = self.request.get( 'msg' )
        default_msg = self.request.get( 'default_msg' )
        app         = App.get( self.request.get('app_uuid') ) # Could be <WOSIB>, <WOSIBShopify> or something...
        link        = Link.get_by_code( self.request.get( 'willt_code' ) )
        user        = User.get( self.request.get( 'user_uuid' ) )
        fb_token    = self.request.get('fb_access_token')
        fb_id       = self.request.get('fb_id')

        product_uuids = self.request.get('products').split(',') # [uuid,uuid,uuid]
        fb_friends    = []
        email_friends = []
        email_share_counter = 0
        fb_share_counter = 0
        
        # Default response
        response = {
            'success': False,
            'data': {
                'message': "",
                'warnings': []
            }
        }
        
        products = [Product.get(uuid) for uuid in product_uuids] # supposedly: [Product, Product, Product]
        random_product = random.choice(products)
        
        # Request appears valid, proceed!
        a = {
            'name': asker[0],
            'email': asker[1],
            # If asker didn't log into Facebook, test Gravatar for a profile photo
            # s=40 -> 40px size
            # d=mm -> defaults a grey outline of a person picture (mystery man)
            'pic': asker[2] if len(asker) == 3 else 'http://www.gravatar.com/avatar/'+hashlib.md5(asker[1].lower()).hexdigest()+'?s=40&d=mm'
        }

        # Split up friends into FB and email
        for friend in friends:
            try:
                if friend[0] == 'fb':
                    # Validation can be added here if necessary
                    fb_friends.append(friend)
                elif friend[0] == 'email':
                    # Validation can be added here if necessary
                    email_friends.append(friend)
                else:
                    raise ValueError
            except (TypeError, IndexError, ValueError):
                response['data']['warnings'].append('Invalid friend entry: %s' % friend)
        
        # Add spam warning if there are > 5 email friends
        if len(email_friends) > 5:
            logging.warning('SPAMMER? Emailing %i friends' % len(email_friends))

        # Check formatting of share message
        try:
            if len( msg ) == 0:
                if default_msg:
                    msg = default_msg
                else:
                    msg = "I'm not sure which one I should buy. What do you think?"
            if isinstance(msg, str):
                message = unicode(msg, errors='ignore')
        except:
            logging.warrning('error transcoding to unicode', exc_info=True)

        product_image = "%s/static/imgs/blank.png" % URL # blank
        
        #--- Start with sharing to FB friends ---#

        if fb_token and fb_id:
            logging.info('token and id set, updating user')
            user.update(
                fb_identity = fb_id,
                fb_access_token = fb_token
            )
        
        if fb_friends: # [] is falsy
            ids = []
            names = []
            
            for (_, fname, fid) in fb_friends:
                ids.append(fid)
                names.append(fname)
            try:
                fb_share_ids = user.fb_post_to_friends( ids,
                                                        names,
                                                        msg,
                                                        random_product.images[0], # product image
                                                        random_product.title, # product title
                                                        random_product.description,
                                                        app.client.domain,
                                                        link )
                fb_share_counter += len(fb_share_ids)
                logging.info('shared on facebook, got share id %s' % fb_share_ids)

            except Exception,e:
                # Should still do email friends
                response['data']['warnings'].append('Error sharing on Facebook: %s' % str(e))
                logging.error('we had an error sharing on facebook', exc_info=True)

        #--- Second do email friends ---#

        if email_friends: # [] is falsy
            for (_, fname, femail) in email_friends:
                try:
                    logging.info ("sending email with link %s" % link.get_willt_url())
                    Email.WOSIBAsk(from_name=     a['name'],
                                   from_addr=     a['email'],
                                   to_name=       fname,
                                   to_addr=       femail,
                                   message=       msg,
                                   vote_url=      link.get_willt_url(),
                                   asker_img=     a['pic'],
                                   client_name=   app.client.name,
                                   client_domain= app.client.domain )
                except Exception,e:
                    response['data']['warnings'].append('Error sharing via email: %s' % str(e))
                    logging.error('we had an error sharing via email', exc_info=True)
                finally:
                    email_share_counter += 1
        
        friend_share_counter = fb_share_counter + email_share_counter

        if friend_share_counter > 0:
            # create the instance!
            instance = app.create_instance( user, 
                                            None, 
                                            link, 
                                            product_uuids)
            # change link to reflect to the vote page.
            link.target_url = "%s://%s%s?instance_uuid=%s" % (PROTOCOL, DOMAIN, url ('WOSIBVoteDynamicLoader'), instance.uuid)
            logging.info ("link.target_url changed to %s (%s)" % (link.target_url, instance.uuid))
            link.put()
            link.memcache_by_code() # doubly memcached

            # increment shares
            for _ in range(friend_share_counter):
                app.increment_shares()

            response['success'] = True

            if friend_share_counter == len(friends):
                response['data']['message'] = 'Messages sent to every friend'
            else:
                response['data']['message'] = 'Messages sent to some friends'
        else:
            response['data']['message'] = 'Could not successfully contact any friends'
        
        if not response['data']['warnings']:
            del response['data']['warnings']
        
        try:
            iuid = instance.uuid
        except:
            iuid = None
        
        logging.info('Friends: %s\n \
            Successful shares on FB: %d\n \
            Successful shares via email: %d\n \
            Message: %s\n \
            Instance: %s' % (friends, fb_share_counter, email_share_counter, msg, iuid))
        
        Email.emailDevTeam('<p>Friends: %s</p> \
            <p>Successful shares on FB: #%d</p> \
            <p>Successful shares via email: #%d</p> \
            <p>Message: %s</p> \
            <p>Instance: %s</p>' % (friends, fb_share_counter, email_share_counter, msg, iuid))
        
        logging.info('response: %s' % response)
        self.response.headers['Content-Type'] = "application/json"
        self.response.out.write(json.dumps(response))

