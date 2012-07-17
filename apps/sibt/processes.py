#!/usr/bin/env python

__author__ = "Willet, Inc."
__copyright__ = "Copyright 2012, Willet, Inc"

import datetime
import logging
import random
import re
import hashlib
import urlparse

from django.utils import simplejson as json
from google.appengine.api import taskqueue
from google.appengine.ext import db

from apps.action.models import Action
from apps.client.models import Client
from apps.email.models import Email
from apps.link.models import Link
from apps.product.models import Product
from apps.sibt.actions import SIBTShowAction, SIBTUserAction, SIBTVoteAction
from apps.sibt.models import SIBT
from apps.sibt.models import SIBTInstance
from apps.user.models import User

from util.consts import DOMAIN, PROTOCOL, URL
from util.helpers import url
from util.shopify_helpers import get_domain, get_shopify_url
from util.strip_html import strip_html
from util.urihandler import obtain, URIHandler


class SIBTSignUp(URIHandler):
    """Shows the signup page.

    SIBT Signup is done in 3 stages:
    - get_or_create user
    - get_or_create client
    - get_or_create app

    This is called by AJAX. Response is an empty page with appropriate code.
    """
    @obtain('email', 'fullname', 'shopname', 'shop_url')
    def post(self, email, fullname, shopname, shop_url):
        """POST request lets you sign up."""

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
    """Create OR edit a SIBT instance."""
    def post(self):
        """Given:
        - app_uuid,
        - page_url (one of the products' url), and
        - products (a CSV of product UUIDs),
        create a SIBTInstance.for the current (cookied) user.

        If [link]code is supplied (and valid), that link will be reused.
        If instance_uuid is supplied (and valid), no new instance will be made.

        The resultant JSON will contain the instance uuid if successful:
        {data:{instance_uuid:abc}}
        """
        # defaults
        response = {
            'success': False,
            'data': {
                'instance_uuid': None,
                'message': None
            }
        }

        app = SIBT.get(self.request.get('app_uuid'))
        if not (app and app.client):
            response['data']['message'] = "App not found"
            self.response.out.write(json.dumps(response))

        page_url = self.request.get('page_url')
        if not page_url:
            response['data']['message'] = "page_url not found"
            self.response.out.write(json.dumps(response))

        products = self.request.get('products').split(',')
        if not (products and len(products)):
            response['data']['message'] = "products not found"
            self.response.out.write(json.dumps(response))

        user = User.get_or_create_by_cookie(self, app)

        logging.debug('domain = %r' % get_domain(page_url))
        # the href will change as soon as the instance is done being created!
        link = Link.get_by_code(self.request.get('code'))
        if link:
            logging.info('using existing link %s' % self.request.get('code'))
        else:
            logging.info('no code supplied; creating link')
            link = Link.create(targetURL=page_url,
                               app=app,
                               domain=get_shopify_url(page_url),
                               user=user)

        instance = SIBTInstance.get(self.request.get('instance_uuid'))
        if instance:  # instance created ahead of time
            logging.info('using existing instance %s' % instance.uuid)
            instance.link = link
            instance.products = products
            instance.put()
        else:  # instance to be created
            logging.info('no uuid supplied; creating instance')
            instance = app.create_instance(user=user, end=None, link=link,
                                           dialog="", img="",
                                           motivation=self.request.get('motivation', None),
                                           sharing_message="", products=products)

        # after creating the instance, switch the link's URL right back to the
        # instance's vote page
        link.target_url = urlparse.urlunsplit([PROTOCOL,
                                               DOMAIN,
                                               url('VoteDynamicLoader'),
                                               ('instance_uuid=%s' % instance.uuid),
                                               ''])
        logging.info("link.target_url changed to %s" % link.target_url)
        link.put()

        response['success'] = True
        response['data']['instance_uuid'] = instance.uuid

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
            user = User.get(user_uuid)
            #user = User.all().filter('uuid =', user_uuid).get()
        if not user:
            user = User.get_or_create_by_cookie(self, app)

        user_vote_count = instance.get_votes_count(user=user)
        if user_vote_count >= 1:  # already voted
            self.error(403)  # "you can't vote again"
            return

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
            Email.SIBTVoteNotification(instance=instance, vote_type=which)
        else:
            logging.info('going to WOSIB email shopper.')
            try:
                product = Product.get(which)  # note that None is okay here.
            except:
                product = None
            Email.WOSIBVoteNotification(instance=instance, product=product)

        self.response.out.write('ok')


class GetExpiredSIBTInstances(URIHandler):
    def post(self):
        return self.get()

    def get(self):
        """Gets a list of SIBT instances to be expired and emails to be sent.

        2012-06-21: add '?early=1' to expire all instances one day earlier
                    than expected.
        """
        try:
            right_now = datetime.now() # let's assume datetime is the class
        except AttributeError:
            # App Engine sometimes imports datetime as a module...
            # Has been reported to GOOG: http://code.google.com/p/googleappengine/issues/detail?id=7341
            right_now = datetime.datetime.now()

        if self.request.get('early', False):
            right_now = right_now + datetime.timedelta(days=1)

        expired_instances = SIBTInstance.all()\
                                        .filter('end_datetime <=', right_now)\
                                        .filter('is_live =', True)

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
            logging.info("setting is_live to False")
            instance.is_live = False
            instance.put()
            return instance

        instance_uuid = self.request.get('instance_uuid')
        instance = SIBTInstance.get(instance_uuid)
        if instance:
            result_instance = db.run_in_transaction(txn, instance)

            try:
                votes = SIBTVoteAction.all().filter('sibt_instance =', instance)\
                                      .count()
                if votes:
                    logging.info('%d Votes for this instance' % votes)
                else:
                    logging.info('Instance has no votes. Not emailing user.')
                    return
            except TypeError, err:
                logging.info('Instance has no votes: %s' % err)
                return # votes can *sometimes* be a Query object if zero votes
            except AttributeError, err:
                # votes can *sometimes* be a Query object if zero votes
                logging.error('Could not find instance votes: %s' % err,
                              exc_info=True)

            products = instance.products
            if products and len(products):
                Email.SIBTVoteCompletion(instance=instance,
                                         product=Product.get(products[0]))
        else:
            logging.error("could not get instance for uuid %s" % instance_uuid)
        logging.info('done expiring')


class SendFriendAsks(URIHandler):
    """Sends messages to email & FB friends."""
    def post(self):
        """
        Expected inputs:
            friends: JSON-encoded <Array> [ <array> [ <string> type,
                                                    <string> name,
                                                    <string> identifier ]
            asker: JSON-encoded <array> [<string> name,
                                        <string> email_address [,
                                        <string> picture_url ]]
            msg: <string> message
            default_msg: <string> message before user edited it
            app_uuid: <string> a SIBT app uuid
            product_uuid: <string> a <Product> uuid
            products: <string> a CSV of <Product> uuids
            willt_code: <string> willt_code corresponding to a SIBTInstance
            user_uuid: <string> a <User> uuid
            fb_access_token: <string> a Facebook API access token for this user
            fb_id: <string> a Facebook user id for this user
            instance_uuid (optional): if not empty, will ask friends about
                                    this FULL instance.

        Expected output (JSON-encoded):
            success: <Boolean> at least some friends were successfully contacted
            data: <Dict>
                message: <String> description of outcome
                warnings: <Array> [ <string> explanation of any incompleted
                                    friend asks ]

        """
        logging.info("TARGETTED_SHARE_SIBT_EMAIL_AND_FB")

        # Shorthand
        rget = self.request.get

        # app is returned as its subclass - a characteristic of App Engine.
        app = App.get(rget('app_uuid'))
        asker = json.loads(rget('asker'))
        default_msg = rget('default_msg')
        email_friends = []
        email_share_counter = 0
        fb_friends = []
        fb_id = rget('fb_id')
        fb_share_counter = 0
        fb_token = rget('fb_access_token')
        friends = json.loads(rget('friends'))
        msg = rget('msg', '')[:1000]  # sharing message is limited to 1k chars
        user = User.get(rget('user_uuid'))

        # re-use instance link if there already is one
        instance = SIBTInstance.get(rget('instance_uuid')) or None
        if instance:
            link = instance.link
        else:
            link = Link.get_by_code(rget('willt_code'))

        product = Product.get(rget('product_uuid'))
        logging.debug('got uuid %s, product %r' % (rget('product_uuid'),
                                                   product))

        # [uuid,uuid,uuid]
        product_uuids = rget('products').split(',')

        # supposedly: [Product, Product, Product]
        products = [Product.get(uuid) for uuid in product_uuids]
        logging.debug('got uuids %r, products %r' % (product_uuids,
                                                     products))

        # Default response
        response = {'success': False,
                    'data': {'message': "",
                             'warnings': []}}

        logging.debug('asker: %r \n'
                      'friends: %r \n'
                      'msg: %s \n'
                      'link: %s' % (asker, friends, msg, link))

        # back-fill the product variable
        if not products[0] and product:
            products = [product]
        elif not product:
            product = random.choice(products)
        # logging.debug('got product %r, products %r' % (product, products))

        if not user:
            logging.error('failed to get user by uuid %s' % rget('user_uuid'))
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
                Email.emailDevTeam('<p>SIBT SPAMMER? Emailing %i friends</p>'
                                   '<p>Asker: %s</p>'
                                   '<p>Message: %s</p>'
                                   '<p>Instance: %s</p>' % (email_share_counter,
                                                            asker,
                                                            msg,
                                                            instance.uuid),
                                   subject='Spy around here')

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
                logging.debug('product image = %s' % product_image)
            except (TypeError, IndexError):
                logging.warn('Could not get product image')
                product_image = 'http://rf.rs/static/imgs/blank.png' # blank
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

                except Exception, e:
                    # Should still do email friends
                    response['data']['warnings'].append('Error sharing on Facebook: %s' % str(e))
                    logging.error('we had an error sharing on facebook', exc_info=True)

            #--- Second do email friends ---#

            if email_friends: # [] is falsy
                for (_, fname, femail) in email_friends:
                    try:
                        Email.SIBTAsk(client=app.client,
                                      from_name=a['name'],
                                      from_addr=a['email'],
                                      to_name=fname,
                                      to_addr=femail,
                                      message=msg,
                                      vote_url=link.get_willt_url(),
                                      product=product or None,
                                      products=products or [],
                                      asker_img=a['pic'])
                    except Exception, e:
                        response['data']['warnings'].append('Error sharing via email: %s' % str(e))
                        logging.error('we had an error sharing via email',
                                      exc_info=True)
                    finally:
                        email_share_counter += 1

            friend_share_counter = fb_share_counter + email_share_counter

            if friend_share_counter > 0:
                # create the instance!
                if not instance:
                    instance = app.create_instance(user=user,
                                                   end=None,
                                                   link=link,
                                                   dialog="ConnectFB",
                                                   img=product_image,
                                                   motivation="",
                                                   sharing_message=msg,
                                                   products=product_uuids)
                else:  # instance exists! update its details.
                    instance.asker = user
                    instance.sharing_message = msg
                    instance.products = product_uuids
                    instance.dialog = "ConnectFB"
                    instance.img = product_image
                    logging.debug('updating existing instance')

                # change link to reflect to the vote page.
                link.target_url = urlparse.urlunsplit([PROTOCOL,
                                                       DOMAIN,
                                                       url('VoteDynamicLoader'),
                                                       ('instance_uuid=%s' % instance.uuid),
                                                       ''])

                logging.info ("link.target_url changed to %s (%s)" % (link.target_url, instance.uuid))
                link.put()
                link.memcache_by_code() # doubly memcached

                instance.link = link
                instance.put()

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

            iuid = getattr(instance, 'uuid', None)

            logging.info('Asker: %s\n'
                         'Friends: %s\n'
                         'Successful shares on FB: %d\n'
                         'Successful shares via email: %d\n'
                         'Message: %s\n'
                         'Instance: %s' % (asker, friends, fb_share_counter,
                                           email_share_counter, msg, iuid))

            Email.emailDevTeam('<p>SIBT Share!\n</p>'
                               '<p>Asker: %s\n</p>'
                               '<p>Friends: %s</p>'
                               '<p>Successful shares on FB: %d</p>'
                               '<p>Successful shares via email: %d</p>'
                               '<p>Message: %s</p>'
                               '<p>Instance: %s</p>'
                               '<p>Link: %s</p>' % (asker, friends, fb_share_counter,
                                                    email_share_counter, msg, iuid,
                                                    link.get_willt_url()),
                               subject='SIBT share detected')

        logging.info('response: %s' % response)
        self.response.headers['Content-Type'] = "application/json"
        self.response.out.write(json.dumps(response))


class SaveProductsToInstance(URIHandler):
    """Modifies the products in an instance."""
    def post(self):
        """
        Expected inputs:
            instance_uuid (required)
            products (required): a comma-separated string of product UUIDs.
            unshift (optional, 0): if 1, handler will only affect the order of
                                the list of products.
                Example: products in instance: 1,2,3,4
                        products: 4,3
                        unshift: 1
                        -> products in instance (updated): 4,3,1,2

        Expected outputs:
            (200/400 response headers)

        """
        logging.info("Saving product selection of a given instance")

        # Shorthand
        rget = self.request.get

        # fetch instance and products... run code if both are valid inputs
        instance = SIBTInstance.get(rget('instance_uuid'))
        product_uuids = rget('products', '').split(',')
        products = [Product.get(uuid) for uuid in product_uuids]
        unshift = bool(rget('unshift', '0') == '1')

        logging.debug('instance = %r' % instance)
        logging.debug('product_uuids = %r' % product_uuids)
        logging.debug('products = %r' % products)

        if instance and all(products):
            if unshift:  # re-order mode
                logging.debug('instance.products = %r' % instance.products)
                remainder = frozenset(instance.products).difference(product_uuids)
                logging.debug('remainder = %r' % remainder)
                instance.products = product_uuids
                instance.products.extend(list(remainder))
                logging.debug('instance.products = %r' % instance.products)
            else:  # replace mode
                instance.products = product_uuids
                logging.debug('replace mode '
                              'instance.products = %r' % instance.products)
            instance.put()
            # logging.info('response: %s' % response)
            self.error(200)
            return

        # logging.info('response: %s' % response)
        self.error(400)


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
    client.is_vendor = True
    client.put()

    user.update(client=client)  # can't bundle with previous user update

    app = SIBT.get_or_create(client=client, domain=domain)
    if not client:
        return (False, 'wtf, no app?')

    template_values = {'app': app,
                       'URL': URL,
                       'shop_name': client.name,
                       'shop_owner': client.merchant.name,
                       'client': client,
                       'sibt_version': app.version,
                       'new_order_code': False}

    return (True, request_handler.render_page('templates/vendor_include.js',
                                              template_values))
