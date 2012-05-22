#!/usr/bin/env python

__author__ = "Willet, Inc."
__copyright__ = "Copyright 2012, Willet, Inc"

from datetime import datetime
import random
import re
import hashlib
import urlparse

from django.utils import simplejson as json
from google.appengine.api import taskqueue
from google.appengine.ext import webapp, db

from apps.app.models import App
from apps.action.models import UserAction
from apps.client.models import Client
from apps.email.models import Email
from apps.link.models import Link
from apps.product.shopify.models import ProductShopify
from apps.product.models import Product
from apps.sibt.actions import *
from apps.sibt.models import SIBT
from apps.sibt.models import SIBTInstance, PartialSIBTInstance
from apps.user.actions import UserCreate, UserIsFBLoggedIn
from apps.user.models import User
from apps.wosib.actions import *

from util.consts import *
from util.helpers import url
from util.helpers import remove_html_tags
from util.strip_html import strip_html
from util.urihandler import URIHandler


class SIBTSignUp(URIHandler):
    """Shows the signup page.

    SIBT Signup is done in 3 stages:
    - get_or_create user
    - get_or_create client
    - get_or_create app

    This is called by AJAX. Response is an empty page with appropriate code.
    """
    def post(self):
        """POST request lets you sign up."""
        email = self.request.get("email")
        fullname = self.request.get("fullname")
        shopname = self.request.get("shopname")
        shop_url = self.request.get("shop_url")
        # optional stuff
        address1 = self.request.get("address1", '')
        address2 = self.request.get("address2", '')
        phone = self.request.get("phone", '')

        logging.debug("SIBT Signup: %r" % [fullname, email, shopname, shop_url,
                                           phone, address1, address2])

        if not (fullname and email and shopname and shop_url):
            self.error(400)  # missing info
            return

        try: # rebuild URL
            shop_url_parts = urlparse.urlsplit(shop_url)
            shop_url = '%s://%s' % (shop_url_parts.scheme,
                                    shop_url_parts.netloc)
        except :
            self.error(400)  # malformed URL
            return

        user = User.get_or_create_by_email(email=email,
                                           request_handler=self,
                                           app=None)  # for now
        if not user:
            logging.error('Could not get user for SIBT signup')
            self.error(500)  # did something wrong
            return

        user.update(full_name=fullname,  # required update
                    email=email,  # required update
                    phone=phone,  # some users get this stuff
                    address1=address1,
                    address2=address2)

        client = Client.get_or_create(url=shop_url,
                                      request_handler=self,
                                      user=user)
        if not client:
            logging.error('Could not create client for SIBT signup')
            self.error(500) # did something wrong
            return

        app = SIBT.get_or_create(client=client,
                                 domain=shop_url)
        if not app:
            logging.error('Could not create client for SIBT signup')
            self.error(500) # did something wrong
            return

        # installation apparently succeeds
        response = {
            'app_uuid': app.uuid,
            'client_uuid': client.uuid,
        }

        logging.info('response: %s' % response)
        self.response.headers['Content-Type'] = "application/json"
        self.response.out.write(json.dumps(response))
        return


class StartSIBTInstance(URIHandler):
    def post(self):
        app = App.get_by_uuid(self.request.get('app_uuid'))
        user = User.get_or_create_by_cookie(self, app)
        link = Link.get_by_code(self.request.get('willt_code'))
        img = self.request.get('product_img')

        logging.info("Starting SIBT instance for %s" % link.target_url)

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
            instance = app.create_instance(user=user,
                                           end=None,
                                           link=link,
                                           dialog="ConnectFB",
                                           img=img,
                                           motivation=None,
                                           sharing_message="")
            response['success'] = True
            response['data']['instance_uuid'] = instance.uuid
        except Exception,e:
            response['data']['message'] = str(e)
            logging.error('we had an error creating the instnace', exc_info=True)

        self.response.out.write(json.dumps(response))


class DoVote(URIHandler):
    def post(self):
        user = None
        instance_uuid = self.request.get('instance_uuid')
        instance = SIBTInstance.get(instance_uuid)
        if not instance:
            logging.error("no instance found")
            return

        app = instance.app_
        user_uuid = self.request.get('user_uuid')
        if user_uuid:
            user = User.get (user_uuid)
            #user = User.all().filter('uuid =', user_uuid).get()
        if not user:
            user = User.get_or_create_by_cookie (self, app)

        # which = response, in either the product uuid or yes/no
        which = self.request.get('product_uuid') or \
                self.request.get('which', 'yes')

        # Make a Vote action for this User
        # vote will count as "selecting a product" if which is a product uuid.
        action = SIBTVoteAction.create(user, instance, which)

        # Count the vote.
        if which.lower() == "no":
            instance.increment_nos()
        else:
            # WOSIB mode increments this too.
            instance.increment_yesses()

        # Tell the Asker they got a vote!
        if which.lower() == "yes" or which.lower() == "no":  # SIBT
            logging.info('going to SIBT email shopper.')
            Email.SIBTVoteNotification(instance=instance,
                                       vote_type=which)
        else:
            logging.info('going to WOSIB email shopper.')
            Email.WOSIBVoteNotification(instance=instance)

        self.response.out.write('ok')


class GetExpiredSIBTInstances(URIHandler):
    def post(self):
        return self.get()

    def get(self):
        """Gets a list of SIBT instances to be expired and emails to be sent"""
        try:
            right_now = datetime.now() # let's assume datetime is the class
        except AttributeError:
            # App Engine sometimes imports datetime as a module...
            # Has been reported to GOOG: http://code.google.com/p/googleappengine/issues/detail?id=7341
            right_now = datetime.datetime.now()

        expired_instances = SIBTInstance.all()\
                .filter('is_live =', True)\
                .filter('end_datetime <=', right_now)

        for instance in expired_instances:
            taskqueue.add(
                url=url('RemoveExpiredSIBTInstance'),
                params={
                    'instance_uuid': instance.uuid
                }
            )
        msg = 'expiring %d instances' % expired_instances.count()
        logging.info(msg)
        self.response.out.write(msg)


class RemoveExpiredSIBTInstance(URIHandler):
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
        if instance:
            result_instance = db.run_in_transaction(txn, instance)
            Email.SIBTVoteCompletion(instance=instance,
                                     product=instance.products[0])
        else:
            logging.error("could not get instance for uuid %s" % instance_uuid)
        logging.info('done expiring')


class TrackSIBTShowAction(URIHandler):
    """DB Action tracking is *being* replaced by Google Analytics."""
    def get(self):
        """Compatibility with iframe scheisse."""
        self.post()

    def post(self):
        """So javascript can track a sibt specific show actions"""
        app = App.get(self.request.get('app_uuid'))
        action = None
        duration = self.request.get('duration', 0.0)
        event = self.request.get('evnt')
        instance = SIBTInstance.get(self.request.get('instance_uuid'))
        success = False
        url = self.request.get('target_url')
        user = User.get(self.request.get('user_uuid'))

        if not (app and event and user):
            return # we can't track who did what or what they did; logging this item is not useful.

        try:
            logging.debug ('user = %s, instance = %s, event = %s' % (user, instance, event))
            action_class = globals()[event]
            action = action_class.create(user,
                                         instance=instance,
                                         url=url,
                                         app=app,
                                         duration=duration)
        except Exception,e:
            logging.debug('Could not create Action class %s: %s' % (event, e))
        else:
            logging.info('tracked action: %s' % action)
            self.response.out.write('')
            return

        try:
            logging.debug('Retrying by creating generic action class')
            action = SIBTShowAction.create(user, instance, event)
        except Exception, e:
            logging.error('Could not log action!: %s' % e, exc_info=True)
        else:
            logging.info('tracked action: %s' % action)

        self.response.out.write('')
        return


class TrackSIBTUserAction(URIHandler):
    """ For actions WITH AN INSTANCE """
    def get(self):
        """Compatibility with iframe shizz"""
        self.post()

    def post(self):
        """So javascript can track a sibt specific show actions"""
        app = None
        action = None
        duration = 0.0
        instance = None
        success = False
        user = None

        if self.request.get('instance_uuid'):
            instance = SIBTInstance.get(self.request.get('instance_uuid'))
        if self.request.get('app_uuid'):
            app = App.get(self.request.get('app_uuid'))
        if self.request.get('user_uuid'):
            user = User.get(self.request.get('user_uuid'))
        event = self.request.get('what')
        url = self.request.get('target_url')
        if self.request.get('duration'):
            duration = self.request.get('duration')

        if not event or not user:
            return # we can't track who did what or what they did; logging this item is not useful.

        action = None
        try:
            action_class = globals()[event]
            action = action_class.create(user,
                    instance=instance,
                    url=url,
                    app=app,
                    duration=duration
            )
        except Exception,e:
            logging.warn('(this is not serious) could not create class: %s' % e)
            try:
                action = SIBTUserAction.create(user, instance, event)
            except Exception, e:
                logging.error('this is serious: %s' % e, exc_info=True)
            else:
                logging.info('tracked action: %s' % action)
                success = True
        else:
            logging.info('tracked action: %s' % action)
            success = True

        self.response.out.write('')


class StartPartialSIBTInstance(URIHandler):
    """A Partial(.*)Instance differs from a formal Instance in that
    they auto-expire after an hour.
    """
    def post(self):
        """Starts a PartialSIBTInstance.

        This controller does NOT check if the product UUIDs supplied
        corresponds to a DB Product (because it costs reads).
        """
        msg = None # error (a non-None value will invoke logging)

        app = App.get(self.request.get('app_uuid'))
        if not app:
            msg = "Not sure which App for which to create partial instance"

        link = Link.get_by_code(self.request.get('willt_code'))
        if not link:
            msg = "willt_code does not correspond to working link"

        # product_uuids: ['uuid','uuid','uuid'] or [''] edge case
        # product_uuid (singular, deprecated) is used only if
        # product_uuids is missing.
        logging.debug('products = %s' % self.request.get('products'))
        product_uuids = self.request.get('products', '').split(',')
        logging.debug('product_uuids = %r' % product_uuids)
        if not product_uuids[0]:  # ? '' evals to False; [''] evals to True.
            product_uuids = [self.request.get('product_uuid')]

        if not product_uuids[0]:
            msg = "Cannot get products"

        user = User.get(self.request.get('user_uuid'))
        if not user:
            msg = "User %s not found in DB" % self.request.get('user_uuid')

        try:
            PartialSIBTInstance.create(user=user,
                                       app=app,
                                       link=link,
                                       products=product_uuids)
        except Exception, err: # if it fails for god-knows-what, report it too
            msg = "%s" % err

        if msg:
            logging.error('Cannot create PartialSIBTInstance: %s (%r)' % (
                           msg, [app, link, product_uuids, user]))
            self.response.out.write(msg)  # this is for humans to read
        return


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


class SendFriendAsks(URIHandler):
    """ Sends messages to email & FB friends

    Expected inputs:
        friends: JSON-encoded <Array> [ <array> [ <string> type, <string> name, <string> identifier ]
        asker: JSON-encoded <array> [<string> name, <string> email_address [, <string> picture_url ]]
        msg: <string> message
        default_msg: <string> message before user edited it
        app_uuid: <string> a SIBT app uuid
        product_uuid: <string> a <Product> uuid
        products: <string> a CSV of <Product> uuids
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
    def post(self):
        logging.info("TARGETTED_SHARE_SIBT_EMAIL_AND_FB")

        # Fetch arguments
        app = App.get(self.request.get('app_uuid')) # Could be <SIBT>, <SIBTShopify> or something...
        asker = json.loads(self.request.get('asker'))
        default_msg = self.request.get('default_msg')
        email_friends = []
        email_share_counter = 0
        fb_friends = []
        fb_id = self.request.get('fb_id')
        fb_share_counter = 0
        fb_token = self.request.get('fb_access_token')
        friends = json.loads(self.request.get('friends'))
        link = Link.get_by_code(self.request.get('willt_code'))
        msg = self.request.get('msg')
        product = Product.get(self.request.get('product_uuid'))
        products = []
        product_uuids = self.request.get('products').split(',') # [uuid,uuid,uuid]
        user = User.get(self.request.get('user_uuid'))

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

        # supposedly: [Product, Product, Product]
        products = [Product.get(uuid) for uuid in product_uuids]
        if not products[0] and product:
            products = [product]
        elif not product:  # back-fill the product variable
            product = random.choice(products)

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
                Email.emailDevTeam('<p>SIBT SPAMMER? Emailing %i friends</p> \
                    <p>Asker: %s</p> \
                    <p>Message: %s</p> \
                    <p>Instance: %s</p>' % (email_share_counter, asker, msg, instance.uuid))

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
                if len(msg) == 0:
                    if default_msg:
                        msg = default_msg
                    else:
                        msg = "I'm not sure if I should buy this. What do you think?"
                if isinstance(msg, str):
                    message = unicode(msg, errors='ignore')
            except:
                logging.warning('error transcoding to unicode', exc_info=True)

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
                    fb_share_ids = user.fb_post_to_friends(ids,
                                                           names,
                                                           msg,
                                                           product_image,
                                                           product.title,
                                                           product_desc,
                                                           app.client.domain,
                                                           link)
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
                        if len(products) > 1:
                            Email.WOSIBAsk(from_name=a['name'],
                                           from_addr=a['email'],
                                           to_name=fname,
                                           to_addr=femail,
                                           message=msg,
                                           vote_url=link.get_willt_url(),
                                           asker_img=a['pic'],
                                           client=app.client,
                                           products=products)
                        else:
                            Email.SIBTAsk(from_name=a['name'],
                                          from_addr=a['email'],
                                          to_name=fname,
                                          to_addr=femail,
                                          message=msg,
                                          vote_url=link.get_willt_url(),
                                          product_img=product_image,
                                          asker_img=a['pic'],
                                          product_title=product.title,
                                          client=app.client)
                    except Exception,e:
                        response['data']['warnings'].append('Error sharing via email: %s' % str(e))
                        logging.error('we had an error sharing via email', exc_info=True)
                    finally:
                        email_share_counter += 1

            friend_share_counter = fb_share_counter + email_share_counter

            if friend_share_counter > 0:
                # create the instance!
                instance = app.create_instance(user=user,
                                               end=None,
                                               link=link,
                                               dialog="ConnectFB",
                                               img=product_image,
                                               motivation="",
                                               sharing_message=msg,
                                               products=product_uuids)

                # change link to reflect to the vote page.
                link.target_url = urlparse.urlunsplit([PROTOCOL,
                                                       DOMAIN,
                                                       url('VoteDynamicLoader'),
                                                       ('instance_uuid=%s' % instance.uuid),
                                                       ''])

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

            logging.info('Asker: %s\n \
                Friends: %s\n \
                Successful shares on FB: %d\n \
                Successful shares via email: %d\n \
                Message: %s\n \
                Instance: %s' % (asker, friends, fb_share_counter, email_share_counter, msg, iuid))

            Email.emailDevTeam('<p>SIBT Share!\n</p> \
                <p>Asker: %s\n</p> \
                <p>Friends: %s</p> \
                <p>Successful shares on FB: %d</p> \
                <p>Successful shares via email: %d</p> \
                <p>Message: %s</p> \
                <p>Instance: %s</p>' % (asker, friends, fb_share_counter, email_share_counter, msg, iuid))

        logging.info('response: %s' % response)
        self.response.headers['Content-Type'] = "application/json"
        self.response.out.write(json.dumps(response))


def VendorSignUp(request_handler, domain, email, first_name, last_name, phone):
    """Function to create a vendor's Client, SIBT App, and User.

    Returns (<bool>success?, <string>code), where code is the error message
    if it fails, or a javascript snippet if it succeeds.

    If previous user/client/app objects exist, they will be reused.
    """
    user = User.get_or_create_by_email(email=email,
                                       request_handler=request_handler,
                                       app=None)
    if not user:
        return (False, 'wtf, no user?')

    full_name = "%s %s" % (first_name, last_name)
    user.update(email=email,
                first_name=first_name,
                last_name=last_name,
                full_name=full_name,
                phone=phone,
                accepts_marketing=False)

    client = Client.get_or_create(url=domain,
                                  request_handler=request_handler,
                                  user=user)
    if not client:
        return (False, 'wtf, no client?')

    # got a client; update its info
    client.email = email
    client.name = full_name
    client.vendor = True
    client.put()

    user.update(client=client)  # can't bundle with previous user update

    app = SIBT.get_or_create(client=client, domain=domain)
    if not client:
        return (False, 'wtf, no app?')

    # put back the UserAction that we skipped making
    UserCreate.create(user, app)

    template_values = {'app': app,
                       'URL': URL,
                       'shop_name': client.name,
                       'shop_owner': client.merchant.name,
                       'client': client,
                       'sibt_version': app.version,
                       'new_order_code': True}

    return (True, request_handler.render_page('templates/vendor_include.js',
                                              template_values))