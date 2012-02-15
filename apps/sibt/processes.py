#!/usr/bin/env python

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc"

import re
import hashlib

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
from apps.sibt.actions        import *
from apps.sibt.models         import SIBTInstance, PartialSIBTInstance
from apps.user.actions        import UserIsFBLoggedIn
from apps.user.models         import User, get_or_create_user_by_cookie

from util.consts              import *
from util.helpers             import url 
from util.helpers             import remove_html_tags
from util.urihandler          import URIHandler
from util.strip_html          import strip_html


class ShareSIBTInstanceOnFacebook(URIHandler):
    def post(self):
        logging.info("SHARESIBTONFACEBOOK")

        app  = get_app_by_id(self.request.get('app_uuid'))
        user = User.get(self.request.get('user_uuid'))
        if not user:
            logging.warn('failed to get user by uuid %s' % self.request.get('user_uuid'))
            user = get_or_create_user_by_cookie(self, app)
        willt_code = self.request.get('willt_code')
        link = Link.get_by_code(willt_code)
        img = self.request.get('product_img')
        product_name = self.request.get('name')
        product_desc = None 
        product_id = self.request.get('product_id')
        motivation = self.request.get('motivation')
        fb_token = self.request.get('fb_token')
        fb_id = self.request.get('fb_id')
        message = self.request.get('msg')

        product = None
        try:
            product = ProductShopify.get_by_shopify_id( str(product_id) )
        except:
            logging.info('Could not get product by id %s' % product_id, exc_info=True)
        try:
            #product_desc = '.'.join(product.description[:150].split('.')[:-1]) + '.'
            #product_desc = remove_html_tags(product_desc)
            ex = '[!\.\?]+'
            product_desc = strip_html(product.description)
            parts = re.split(ex, product_desc[:150])
            product_desc = '.'.join(parts[:-1])
            if product_desc[:-1] not in ex:
                product_desc += '.'
        except:
            logging.info('could not get product description')
        
        try:
            if isinstance(message, str):
                message = unicode(message, errors='ignore')

            if isinstance(img, str):
                img = unicode(img, errors='ignore')
            
            if isinstance(product_name, str):
                product_name = unicode(product_name, errors='ignore')

            if isinstance(product_desc, str):
                product_desc = unicode(product_desc, errors='ignore')
        except:
            logging.info('error transcoding to unicode', exc_info=True)

        # defaults
        response = {
            'success': False,
            'data': {}
        }

        # first do sharing on facebook
        if fb_token and fb_id:
            logging.info('token and id set, updating user')
            user.update(
                fb_identity = fb_id,
                fb_access_token = fb_token
            ) 
        if not hasattr(user, 'fb_access_token') or \
            not hasattr(user, 'fb_identity'):
            logging.info('Setting users facebook info')    
            user.update(
                fb_identity = fb_id,
                fb_access_token = fb_token
            ) 

        try:
            facebook_share_id, plugin_response = user.facebook_share(
                message,
                img,
                product_name,
                product_desc,
                link
            )
            logging.info('shared on facebook, got share id and response %s %s' % (
                facebook_share_id,
                plugin_response
            ))

            # if it wasn't successful ...
            if facebook_share_id == None or plugin_response == 'fail':
                # posting failed!
                response['data']['message'] = 'Could not post to facebook'
            else:
                # create the instance!
                # Make the Instance!
                instance = app.create_instance(user, 
                        None, link, img, motivation=motivation, 
                        dialog="ConnectFB")
        
                # increment link stuff
                link.app_.increment_shares()
                link.add_user(user)
                logging.info('incremented link and added user')

                response['success'] = True
        except Exception,e:
            response['data']['message'] = str(e)
            logging.error('we had an error sharing on facebook', exc_info=True)

        logging.info('response: %s' % response)
        self.response.out.write(json.dumps(response))


class StartSIBTInstance(URIHandler):
    def post(self):
        app  = get_app_by_id(self.request.get('app_uuid'))
        user = get_or_create_user_by_cookie(self, app)
        link = Link.get_by_code(self.request.get('willt_code'))
        img = self.request.get('product_img')
        
        logging.info("Starting SIBT instance for %s" % link.target_url )

        # defaults
        response = {
            'success': False,
            'data': {
                'instance_uuid': None,
                'message': None
            }
        }

        try:
            # Make the Instance!
            instance = app.create_instance(user, None, link, img, 
                                           motivation=None, dialog="ConnectFB")
        
            response['success'] = True
            response['data']['instance_uuid'] = instance.uuid
        except Exception,e:
            response['data']['message'] = str(e)
            logging.error('we had an error creating the instnace', exc_info=True)

        self.response.out.write(json.dumps(response))


class DoVote( URIHandler ):
    def post(self):
        user_uuid = self.request.get('user_uuid')
        if user_uuid != None:
            user = User.all().filter('uuid =', user_uuid).get() 

        which = self.request.get( 'which' )
        instance_uuid = self.request.get( 'instance_uuid' )
        instance = SIBTInstance.get( instance_uuid )
        app = instance.app_

        # Make a Vote action for this User
        action = SIBTVoteAction.create( user, instance, which )

        # Count the vote.
        if which.lower() == "yes":
            instance.increment_yesses()
        else:
            instance.increment_nos()

        # Tell the Asker they got a vote!
        email = instance.asker.get_attr('email')
        if email != "":
            Email.SIBTVoteNotification(
                email, 
                instance.asker.get_full_name(), 
                which, 
                instance.link.get_willt_url(), 
                instance.product_img,
                app.client.name,
                app.client.domain
            ) 

        self.response.out.write('ok')


class GetExpiredSIBTInstances(URIHandler):
    def post(self):
        return self.get()
    
    def get(self):
        """Gets a list of SIBT instances to be expired and emails to be sent"""
        from datetime import datetime
        right_now = datetime.now()
        expired_instances = SIBTInstance.all()\
                .filter('is_live =', True)\
                .filter('end_datetime <=', right_now) 

        for instance in expired_instances:
            taskqueue.add(
                url = url('RemoveExpiredSIBTInstance'),
                params = {
                    'instance_uuid': instance.uuid    
                }
            )
        logging.info('expiring %d instances' % expired_instances.count())


class RemoveExpiredSIBTInstance(webapp.RequestHandler):
    def post(self):
        return self.get()
    
    def get(self):
        """Updates the SIBT instance in a transaction and then emails the user"""
        def txn(instance):
            instance.is_live = False
            instance.put()
            return instance
        
        instance_uuid = self.request.get('instance_uuid')
        instance = SIBTInstance.get(instance_uuid)
        if instance != None:
            result_instance = db.run_in_transaction(txn, instance)
            email = instance.asker.get_attr('email')
            if email != "":
                Email.SIBTVoteCompletion(
                    email,
                    result_instance.asker.get_full_name(),
                    result_instance.link.get_willt_url(),
                    result_instance.product_img,
                    result_instance.get_yesses_count(),
                    result_instance.get_nos_count()
                )
        else:
            logging.error("could not get instance for uuid %s" % instance_uuid)
        logging.info('done expiring')


class StoreAnalytics( URIHandler ):
    def get( self ):
        logging.error('WE SHOULDNT BE DOING THIS ANYMORE, BAD PROGRAMMER')


class TrackSIBTShowAction(URIHandler):
    def get(self):
        """Compatibility with iframe shizz"""
        self.post()

    def post(self):
        """So javascript can track a sibt specific show actions"""
        success  = False
        instance = app = user = action = None
        duration = 0.0
        if self.request.get('instance_uuid'):
            instance = SIBTInstance.get(self.request.get('instance_uuid')) 
        if self.request.get('app_uuid'):
            app = App.get(self.request.get('app_uuid')) 
        if self.request.get('user_uuid'):
            user = User.get(self.request.get('user_uuid')) 
        if self.request.get('duration'):
            duration = self.request.get('duration')
        what = self.request.get('evnt')
        url = self.request.get('target_url')
        try:
            logging.debug ('TrackSIBTShowAction: user = %s, instance = %s, what = %s' % (user, instance, what))
            action_class = globals()[what]
            action = action_class.create(user, 
                    instance = instance, 
                    url = url,
                    app = app,
                    duration = duration
            )
        except Exception,e:
            logging.warn('(this is not serious) could not create class: %s' % e)
            try:
                logging.debug ('TrackSIBTShowAction 2: user = %s, instance = %s, what = %s' % (user, instance, what))
                action = SIBTShowAction.create(user, instance, what)
            except Exception, e:
                logging.error('this is serious: %s' % e, exc_info=True)
            else:
                logging.info('tracked action: %s' % action)
                success = True
        else:
            logging.info('tracked action: %s' % action)
            success = True

        self.response.out.write('')


class TrackSIBTUserAction(URIHandler):
    """ For actions WITH AN INSTANCE """
    def get(self):
        """Compatibility with iframe shizz"""
        self.post()

    def post(self):
        """So javascript can track a sibt specific show actions"""
        success  = False
        duration = 0.0
        instance = app = user = action = None
        if self.request.get('instance_uuid'):
            instance = SIBTInstance.get(self.request.get('instance_uuid')) 
        if self.request.get('app_uuid'):
            app = App.get(self.request.get('app_uuid'))         
        if self.request.get('user_uuid'):
            user = User.get(self.request.get('user_uuid'))
        what = self.request.get('what')
        url = self.request.get('target_url')
        if self.request.get('duration'):
            duration = self.request.get('duration')
        action = None
        try:
            action_class = globals()[what]
            action = action_class.create(user, 
                    instance = instance, 
                    url = url,
                    app = app,
                    duration = duration
            )
        except Exception,e:
            logging.warn('(this is not serious) could not create class: %s' % e)
            try:
                action = SIBTUserAction.create(user, instance, what)
            except Exception, e:
                logging.error('this is serious: %s' % e, exc_info=True)
            else:
                logging.info('tracked action: %s' % action)
                success = True
        else:
            logging.info('tracked action: %s' % action)
            success = True

        self.response.out.write('')


class StartPartialSIBTInstance( URIHandler ):
    def post( self ):
        app     = App.get( self.request.get( 'app_uuid' ) )
        link    = Link.get_by_code( self.request.get( 'willt_code' ) )
        product = Product.get( self.request.get( 'product_uuid' ) )
        user    = User.get( self.request.get( 'user_uuid' ) )

        PartialSIBTInstance.create( user, app, link, product )


class StartSIBTAnalytics(URIHandler):
    def get(self):
        things = {
            'tb': {
                'action': 'SIBTUserClickedTopBarAsk',
                'show_action': 'SIBTShowingTopBarAsk',
                'l': [],
                'counts': {},
            },
            'b': {
                'action': 'SIBTUserClickedButtonAsk',
                'show_action': 'SIBTShowingButton',
                'l': [],
                'counts': {},
            }
        }
        actions_to_check = [
            'SIBTShowingAskIframe',
            'SIBTAskUserClickedEditMotivation',
            'SIBTAskUserClosedIframe',
            'SIBTAskUserClickedShare',
            'SIBTInstanceCreated',
        ]
        for t in things:
            things[t]['counts'][things[t]['show_action']] = Action\
                    .all(keys_only=True)\
                    .filter('class =', things[t]['show_action'])\
                    .count(999999)
            
            for click in Action.all().filter('what =', things[t]['action']).order('created'):
                try:
                    # we want to get the askiframe event
                    # but we have to make sure there wasn't ANOTHER click after this

                    next_show_button = Action.all()\
                            .filter('user =', click.user)\
                            .filter('created >', click.created)\
                            .filter('app_ =', click.app_)\
                            .filter('class =', 'SIBTShowingButton')\
                            .get()

                    for action in actions_to_check:
                        if action not in things[t]['counts']:
                            things[t]['counts'][action] = 0

                        a = Action.all()\
                                .filter('user =', click.user)\
                                .filter('created >', click.created)\
                                .filter('app_ =', click.app_)\
                                .filter('class =', action)\
                                .get()
                        if a:
                            logging.info(a)
                            if next_show_button:
                                if a.created > next_show_button.created:
                                    logging.info('ignoring %s over %s' % (
                                        a,
                                        next_show_button
                                    ))
                                    continue
                            things[t]['counts'][action] += 1
                            logging.info('%s + 1' % action)

                    client = ''
                    if click.app_.client:
                        if hasattr(click.app_.client, 'name'):
                            client = click.app_.client.name
                        elif hasattr(click.app_.client, 'domain'):
                            client = click.app_.client.domain
                        elif hasattr(click.app_.client, 'email'):
                            client = click.app_.client.email
                        else:
                            client = click.app_.client.uuid
                    else:
                        client = 'No client'

                    things[t]['l'].append({
                        'created': '%s' % click.created,
                        'uuid': click.uuid,
                        'user': click.user.name,
                        'client': client
                    })
                except Exception, e:
                    logging.warn('had to ignore one: %s' % e, exc_info=True)
            things[t]['counts'][things[t]['action']] = len(things[t]['l'])
            
            l = [{'name': item, 'value': things[t]['counts'][item]} for item in things[t]['counts']]
            l = sorted(l, key=lambda item: item['value'], reverse=True)
            things[t]['counts'] = l
        template_values = {
            'tb_counts': things['tb']['counts'],
            'b_counts': things['b']['counts'],
        }

        self.response.out.write(self.render_page('action_stats.html', template_values))


class SendFriendAsks( URIHandler ):
    """ Sends messages to email & FB friends 

    Expected inputs:
        friends: JSON-encoded <Array> [ <array> [ <string> type, <string> name, <string> identifier ]
        asker: JSON-encoded <array> [<string> name, <string> email_address [, <string> picture_url ]]
        msg: <string> message
        default_msg: <string> message before user edited it
        app_uuid: <string> a SIBT app uuid
        product_uuid: <string> a <App> uuid
        willt_code: <string> willt_code corresponding to a parital SIBT instance
        user_uuid: <string> a <User> uuid
        fb_access_token: <string> a Facebook API access token for this user
        fb_id: <string> a Facebook user id for this user
    
    Expected output (JSON-encoded):
        success: <Boolean> at least some friends were successfully contacted
        data: <Dict>
            message: <String> description of outcome
            warnings: <Array> [ <string> explanation of any incompleted friend asks ] 
    """
    def post( self ):
        logging.info("TARGETTED_SHARE_SIBT_EMAIL_AND_FB")
        
        # Fetch arguments 
        friends     = json.loads( self.request.get('friends') )
        asker       = json.loads( self.request.get('asker') )
        msg         = self.request.get( 'msg' )
        default_msg = self.request.get( 'default_msg' )
        app         = App.get( self.request.get('app_uuid') ) # Could be <SIBT>, <SIBTShopify> or something...
        product     = Product.get( self.request.get( 'product_uuid' ) )
        link        = Link.get_by_code( self.request.get( 'willt_code' ) )
        user        = User.get( self.request.get( 'user_uuid' ) )
        fb_token    = self.request.get('fb_access_token')
        fb_id       = self.request.get('fb_id')

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

        logging.debug('asker: %r \n\
            friends: %r \n\
            msg: %s \n\
            link: %s' % (asker, friends, msg, link))

        if not user:
            logging.error('failed to get user by uuid %s' % self.request.get('user_uuid'))
            self.response.set_status(401) # Unauthorized
            response['data']['message'] = 'Unauthorized: Could not find user by supplied id'
        
        elif not asker:
            logging.error('no asker included')
            self.response.set_status(400) # Bad Request
            response['data']['message'] = 'Bad Request: no asker included'
        
        elif not friends:
            logging.error('no friends included')
            self.response.set_status(400) # Bad Request
            response['data']['message'] = 'Bad Request: no friends included'
        
        else:
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

            # Format the product's desc for sharing
            try:
                ex = '[!\.\?]+'
                product_desc = strip_html(product.description)
                parts = re.split(ex, product_desc[:150])
                product_desc = '.'.join(parts[:-1])
                if product_desc[:-1] not in ex:
                    product_desc += '.'
            except:
                logging.warning('could not get product description')
                response['data']['warnings'].append('Could not get product description')
            
            # Check formatting of share message
            try:
                if len( msg ) == 0:
                    if default_msg:
                        msg = default_msg
                    else:
                        msg = "I'm not sure if I should buy this. What do you think?"
                if isinstance(msg, str):
                    message = unicode(msg, errors='ignore')
            except:
                logging.warrning('error transcoding to unicode', exc_info=True)

            # Get product image
            try:
                product_image = product.images[0]
            except (TypeError, IndexError):
                product_image = 'http://social-referral.appspot.com/static/imgs/blank.png' # blank
                response['data']['warnings'].append('Could not get product image')

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
                                                            product_image,
                                                            product.title,
                                                            product_desc,
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
                        Email.SIBTAsk(from_name=     a['name'],
                                      from_addr=     a['email'],
                                      to_name=       fname,
                                      to_addr=       femail,
                                      message=       msg,
                                      vote_url=      link.get_willt_url(),
                                      product_img=   product_image,
                                      asker_img=     a['pic'],
                                      product_title= product.title,
                                      client_name=   app.client.name,
                                      client_domain= app.client.domain )
                        email_share_counter += 1
                    except Exception,e:
                        response['data']['warnings'].append('Error sharing via email: %s' % str(e))
                        logging.error('we had an error sharing via email', exc_info=True)
            
            friend_share_counter = fb_share_counter + email_share_counter

            if friend_share_counter > 0:
                # create the instance!
                instance = app.create_instance( user, 
                                                None, 
                                                link, 
                                                product_image, 
                                                motivation="",
                                                dialog="ConnectFB")
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
            
            logging.info('Friends: %s\n \
                Successful shares on FB: %d\n \
                Successful shares via email: %d\n \
                Message: %s\n \
                Instance: %s' % (friends, fb_share_counter, email_share_counter, msg, instance.uuid))
            
            Email.emailDevTeam('<p>Friends: %s</p> \
                <p>Successful shares on FB: #%d</p> \
                <p>Successful shares via email: #%d</p> \
                <p>Message: %s</p> \
                <p>Instance: %s</p>' % (friends, fb_share_counter, email_share_counter, msg, instance.uuid))
        
        logging.info('response: %s' % response)
        self.response.headers['Content-Type'] = "application/json"
        self.response.out.write(json.dumps(response))

