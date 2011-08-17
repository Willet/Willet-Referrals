# client models
# data models for our clients and associated methods

__all__ = [
    'Client'
]
import logging, urllib, urllib2, uuid

from datetime import datetime
from django.utils import simplejson as json

from google.appengine.api import memcache, taskqueue, urlfetch
from google.appengine.ext import db, webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

from models.campaign import Campaign, ShareCounter, get_campaign_by_id
from models.client import Client
from models.link import Link, LinkCounter
from models.model import Model
from models.shopify import ShopifyItem, ShopifyOrder, create_shopify_order
from models.stats import Stats
from models.user import User, get_user_by_facebook, get_or_create_user_by_facebook, get_or_create_user_by_email

from util.consts import *
from util.emails import Email
from util.helpers import *
from util.urihandler import URIHandler

class CampaignClicksCounter( webapp.RequestHandler ):
    def post( self ): 
        campaign = get_campaign_by_id( self.request.get('campaign_uuid') )
        
        campaign.cached_clicks_count = 0
        if hasattr( campaign, 'links_' ):
            for l in campaign.links_:
                campaign.cached_clicks_count += l.count_clicks()

        campaign.put()

class UpdateCounts( webapp.RequestHandler ):
    def get( self ): 
        stats = Stats.get_stats()
        stats.total_clients    = Client.all().count()
        stats.total_campaigns  = Campaign.all().count()
        stats.total_links      = Link.all().count()
        stats.total_users      = User.all().count()
        stats.put()
        
class UpdateTweets( webapp.RequestHandler ):
    def get( self ):
        shares = ShareCounter.all()
        total  = 0
        for s in shares:
            total += s.count

        stats = Stats.get_stats()
        stats.total_tweets = total
        stats.put()

class UpdateClicks( webapp.RequestHandler ):
    def get( self ):
        links = LinkCounter.all()
        total  = 0
        for l in links:
            total += l.count

        stats = Stats.get_stats()
        stats.total_clicks = total
        stats.put()

class UpdateLanding( webapp.RequestHandler ):
    def get( self ):
        campaign     = get_campaign_by_id( LANDING_CAMPAIGN_UUID )
        
        if campaign == None:
            return

        total_clicks = campaign.count_clicks()
        results, foo = campaign.get_results( total_clicks )

        # Build the string.
        s = '<div class="span-11 last center" id="landing_influencer_title"> <div class="span-1">&nbsp;</div> <div class="span-1">&nbsp;</div> <div class="span-3">&nbsp;</div> <div class="span-2">&nbsp;</div> <div class="span-2">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Clickthroughs</div> <div class="span-2 last">&nbsp;&nbsp;&nbsp;Klout Score</div> </div>'
        count = 0
        for r in results:
            if r['user']:
                twitter_handle = r['user'].twitter_handle
                s += '<div class="span-11 last influencer landing">'
                
                s += '<div class="span-1 number" title="%s\'s place for this campaign."> %s </div>' % (twitter_handle, r['num'])
                s += '<div class="span-1" title="Click to visit %s on Twitter.com!">' % twitter_handle
                s += '<a href="https://twitter.com/#!/%s">' % twitter_handle
                s += '<img class="profile_pic" src="%s"> </img></a></div>' % r['user'].twitter_pic_url 
                
                s += '<div class="span-3 lower-10" title="%s\'s Real Name"> %s </div>' % (twitter_handle, r['user'].twitter_name)
                s += '<div class="span-3 lower-10" title="Click to visit %s on Twitter!">' % twitter_handle
                s += '<a class="twitter_link" href="https://twitter.com/#!/%s">@%s</a></div>' % (twitter_handle, twitter_handle)
                s += '<div class="span-1 lower-10" title="A count of all clicks this user received for this campaign."> %d </div>' % r['clicks']
            
                s += '<div class="span-2 lower-5 last" title="Click to visit %s on Klout.com!">' % twitter_handle
                s += '<a class="klout_link" href="http://klout.com/#/%s">' % twitter_handle
                s += '<img class="klout_logo" src="/static/imgs/klout_logo.jpg"> </img>'
                s += '<object class="klout_score">%s</object> </a> </div>' % r['kscore']

                s += '</div>'

                count += 1

            if count == 6:
                break;

        stats = Stats.get_stats()
        stats.landing = s
        stats.put()

        self.response.out.write( s )

class EmailerCron( URIHandler ):

    @admin_required
    def get( self, admin ):
        campaigns = Campaign.all()

        for c in campaigns:
            #logging.info("Working on %s" % c.title)

            if not c.emailed_at_10 and c.client:
                #logging.info('count %s' % c.get_shares_count() )
                if c.get_shares_count() >= 10:

                    taskqueue.add( queue_name='emailer', 
                                   url='/emailerQueue', 
                                   name= 'EmailingCampaign%s' % c.uuid,
                                   params={'campaign_id' : c.uuid,
                                           'email' : c.client.email} )

class EmailerQueue( URIHandler ):

    @admin_required
    def post( self, admin ):
        email_addr  = self.request.get('email')
        campaign_id = self.request.get('campaign_id')

        # Send out the email.
        Email.first10Shares( email_addr )

        # Set the emailed flag.
        campaign = get_campaign_by_id( campaign_id )
        campaign.emailed_at_10 = True
        campaign.put()


class FetchFacebookData(webapp.RequestHandler):
    """Fetch facebook information about the given user"""

    def post(self):
        rq_vars = get_request_variables(['fb_id'], self)
        logging.info("Grabbing user data for id: %s" % rq_vars['fb_id'])
        user = get_user_by_facebook(rq_vars['fb_id'])
        if user:
            url = FACEBOOK_QUERY_URL + rq_vars['fb_id'] + "?fields=id,name"+\
                ",gender,username,timezone,updated_time,verified,birthday"+\
                ",email,interested_in,location,relationship_status,religion"+\
                ",website,work&access_token=" + getattr(user, 'facebook_access_token')
            fb_response = json.loads(urllib.urlopen(url).read())
            logging.info(fb_response)
            target_data = ['first_name', 'last_name', 'gender', 'verified',
                'timezone', 'email'] 
            collected_data = {}
            for td in target_data:
                if fb_response.has_key(td):
                    collected_data['fb_'+td] = fb_response[td]
            user.update(**collected_data)
        logging.info("done updating")

            
class FetchFacebookFriends(webapp.RequestHandler):
    """Fetch and save the facebook friends of a given user"""

    def get(self):
        rq_vars = get_request_variables(['fb_id'], self)
        user = get_user_by_facebook(rq_vars['fb_id'])
        if user:
            friends = []
            url = FACEBOOK_QUERY_URL + rq_vars['fb_id'] + "/friends"+\
                "?access_token=" + getattr(user, 'fb_access_token')
            fb_response = json.loads(urllib.urlopen(url).read())
            if fb_response.has_key('data'):
                for friend in fb_response['data']:
                    willet_friend = get_or_create_user_by_facebook(friend['id'],
                        name=friend['name'], would_be=True)
                    friends.append(willet_friend.key())
                user.update(fb_friends=friends)
            logging.info(fb_response)


class GetShopifyOrder( webapp.RequestHandler ):

    def post( self ):
        input_order_num = self.request.get( 'order' )
        campaign   = get_campaign_by_id( self.request.get('campaign_uuid') )
        prev_order = campaign.shopify_orders.order( 'created' ).get()
    
        url = '%s/admin/orders.json?since_id=%s' % ( campaign.target_url, prev_order.order_id if prev_order else '0' )
        username = SHOPIFY_API_KEY
        password = SHOPIFY_API_PASSWORD

        # this creates a password manager
        passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
        # because we have put None at the start it will always
        # use this username/password combination for  urls
        # for which `url` is a super-url
        passman.add_password(None, url, username, password)

        # create the AuthHandler
        authhandler = urllib2.HTTPBasicAuthHandler(passman)

        opener = urllib2.build_opener(authhandler)

        # All calls to urllib2.urlopen will now use our handler
        # Make sure not to include the protocol in with the URL, or
        # HTTPPasswordMgrWithDefaultRealm will be very confused.
        # You must (of course) use it when fetching the page though.
        urllib2.install_opener(opener)

        # authentication is now handled automatically for us
        logging.info("Querying %s" % url )
        result = urllib2.urlopen(url)

        # Grab the data about the order from Shopify
        order = json.loads( result.read() ) #['orders'] # Fetch the order
        orders = order['orders']

        items = []
        order_id = user = bill_addr = order_num = referring_site = subtotal = None
        for k, v in orders[0].iteritems():

            # Grab order details
            if k == 'id':
                order_id = v
            elif k == 'subtotal_price':
                subtotal = v
            elif k == 'order_number':
                if v != input_order_num:
                    logging.error("BARBARArAAA BADDDDDD")
                
                order_num = v
            elif k == 'referring_site':
                referring_site = v
        
            # Grab the purchased items and save some information about them.
            elif k == 'line_items':
                for j in v:
                    i = ShopifyItem( name=str(j['name']), price=str(j['price']), product_id=str(j['product_id']))
                    items.append( i )

            # Store User/ Customer data
            elif k == 'billing_address':
                if user:
                    user.city      = v['city']
                    user.province  = v['province']
                    user.country_code = v['country_code']
                    user.latitude  = v['latitude']
                    user.longitude = v['longitude']
                else:
                    bill_addr = v

            elif k == 'customer':
                if user is None:
                    user = get_or_create_user_by_email( v['email'], request_handler=self )

                user.first_name = v['first_name']
                user.last_name  = v['last_name']
                user.shopify_customer_id = v['id']

                if bill_addr:
                    user.city         = bill_addr['city']
                    user.province     = bill_addr['province']
                    user.country_code = bill_addr['country_code']
                    user.latitude     = bill_addr['latitude']
                    user.longitude    = bill_addr['longitude']
        
        # Save the new User data        
        user.put()

        # Make the ShopifyOrder
        o = create_shopify_order( campaign, order_id, order_num, subtotal, referring_site, user )

        # Store the purchased items in the order
        o.items.extend( items )
        o.put()

##-----------------------------------------------------------------------------##
##------------------------- The URI Router ------------------------------------##
##-----------------------------------------------------------------------------##
def main():
    application = webapp.WSGIApplication([
        (r'/campaignClicksCounter', CampaignClicksCounter),
        (r'/updateLanding', UpdateLanding),
        (r'/updateCounts',  UpdateCounts),
        (r'/updateClicks',  UpdateClicks),
        (r'/updateTweets',  UpdateTweets),
        (r'/emailerCron', EmailerCron),
        (r'/fetchFB', FetchFacebookData),
        (r'/fetchFriends', FetchFacebookFriends),
        (r'/emailerQueue', EmailerQueue),
        (r'/getShopifyOrder', GetShopifyOrder),
        ], debug=USING_DEV_SERVER)
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
