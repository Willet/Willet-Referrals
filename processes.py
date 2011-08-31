# client models
# data models for our clients and associated methods

__all__ = [
    'Client'
]
import hashlib, logging, urllib, urllib2, uuid

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
from models.stats import Stats
from models.user import User, get_user_by_facebook, get_or_create_user_by_facebook, get_or_create_user_by_email, get_user_by_uuid

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
        def txn():
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
        db.run_in_transaction(txn)
        logging.info("done updating")

            
class FetchFacebookFriends(webapp.RequestHandler):
    """Fetch and save the facebook friends of a given user"""

    def get(self):
        rq_vars = get_request_variables(['fb_id'], self)
        def txn():
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
        db.run_in_transaction(txn)
        logging.info(fb_response)


class TriggerCampaignAnalytics(webapp.RequestHandler):
    def get(self):
        scope = self.request.get('scope', 'week')
        campaigns = Campaign.all()
        for c in campaigns:
            taskqueue.add(url = '/computeCampaignAnalytics',
                          params = { 'ca_key': c.key(), 
                                      'scope'  : scope, })


class ComputeCampaignAnalytics(webapp.RequestHandler):
    """Fetch facebook information about the given user"""

    def post(self):
        rq_vars = get_request_variables(['ca_key', 'scope'], self)
        ca = db.get(rq_vars['ca_key'])
        ca.compute_analytics(rq_vars['scope'])
 

##-----------------------------------------------------------------------------##
##------------------------- The URI Router ------------------------------------##
##-----------------------------------------------------------------------------##
def main():
    application = webapp.WSGIApplication([
        (r'/campaignClicksCounter', CampaignClicksCounter),
        (r'/triggerCampaignAnalytics', TriggerCampaignAnalytics),
        (r'/computeCampaignAnalytics', ComputeCampaignAnalytics),
        (r'/updateLanding', UpdateLanding),
        (r'/updateCounts',  UpdateCounts),
        (r'/updateClicks',  UpdateClicks),
        (r'/updateTweets',  UpdateTweets),
        (r'/emailerCron', EmailerCron),
        (r'/fetchFB', FetchFacebookData),
        (r'/fetchFriends', FetchFacebookFriends),
        (r'/emailerQueue', EmailerQueue),
        ], debug=USING_DEV_SERVER)
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
