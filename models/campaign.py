# Campaign model
# models a client's sharing campaign

__all__ = [
    'Campaign'
]

import logging, random, datetime

from decimal import *


from google.appengine.api import memcache
from google.appengine.api import urlfetch
from google.appengine.api import taskqueue
from google.appengine.ext import db

from models.link import Link, get_active_links_by_campaign
from models.user import User
from models.model import Model
from util.helpers import generate_uuid

NUM_SHARE_SHARDS = 15

class Campaign(Model):
    """Model storing the data for a client's sharing campaign"""
    uuid            = db.StringProperty( indexed = True )
    created         = db.DateTimeProperty(auto_now_add=True)
    emailed_at_10   = db.BooleanProperty( default = False )
    client          = db.ReferenceProperty( db.Model, collection_name = 'campaigns' )
    
    cached_clicks_count = db.IntegerProperty( default = 0 )
    
    title           = db.StringProperty( indexed = False )
    # If is_shopify, this is the store name
    product_name    = db.StringProperty( indexed = True )
    # If is_shopify, this is the store URL
    target_url      = db.LinkProperty  ( indexed = False )
    
    blurb_title     = db.StringProperty( indexed = False )
    blurb_text      = db.StringProperty( indexed = False )
    
    share_text      = db.StringProperty( indexed = False )
    # If is_shopify, this is None
    webhook_url     = db.LinkProperty( indexed = False, default = None, required = False )

    analytics       = db.ReferenceProperty(db.Model,collection_name='canalytics')

    # Defaults to None, only set if this Campaign has been deleted
    old_client      = db.ReferenceProperty( db.Model, collection_name = 'deleted_campaigns' )

    shopify_token   = db.StringProperty( default = '' )
    
    def __init__(self, *args, **kwargs):
        self._memcache_key = kwargs['uuid'] if 'uuid' in kwargs else None 
        super(Campaign, self).__init__(*args, **kwargs)
    
    @staticmethod
    def _get_from_datastore(uuid):
        """Datastore retrieval using memcache_key"""
        return db.Query(Campaign).filter('uuid =', uuid).get()
    
    def update( self, title, product_name, target_url, blurb_title, blurb_text, share_text, webhook_url ):
        """Update the campaign with new data"""
        self.title          = title
        self.product_name   = product_name
        self.target_url     = target_url
        
        Self.blurb_title    = blurb_title
        self.blurb_text     = blurb_text
        self.share_text     = share_text

        self.webhook_url    = webhook_url
        self.put()
    
    def delete( self ):
        self.old_client = self.client
        self.client     = None
        self.put()
    
    def compute_analytics(self, scope):
        """Update the CampaignAnalytics model for this uuid 
            with latest available data""" 

        campaign = get_campaign_by_id(self.uuid)
        # interpret the scope to a date
        scope = datetime.datetime.today() - datetime.timedelta(30) if scope == 'month'\
            else datetime.datetime.today()-datetime.timedelta(7)

        # twitter, facebook, linkedin
        ao = {}
        users = {}
        lost = 0
        for smp in ['t', 'f', 'l']:
            # [cl]icks, [co]nversions, [sh]ares, [re]ach, [pr]ofit
            ao[smp] = {'cl': 0, 'co': 0, 'sh': 0, 're': 0, 'pr': 0} 
            users[smp] = {'co': 0, 'cl': 0, 'sh': 0}

        if campaign:
            # this filter should work but doesn't for some reason
            links = campaign.links_ # .filter('creation_time >=', scope)
            for l in links: #[l for l in campaign.links_ if hasattr(l, 'user')]:
                logging.info(l.willt_url_code)
                if l.creation_time < scope:
                    logging.info("Skipping: " + str(l.creation_time))
                    continue
                user = getattr(l, 'user', None)
                userID = getattr(user, 'uuid', None)# if hasattr(l, 'user') else None
                if userID and not users.has_key(userID):
                    users[userID] = {}
                    for m in ['t', 'f', 'l']: #twitter, facebook, linkedin
                        # [co]nversions, [cl]icks, [sh]are
                        user[m][userID] = {'co': 0, 'cl': 0, 'sh': 0}

                for smp in ['facebook_share_id', 'tweet_id', 'linkedin_share_url']:
                    abbr = smp[0] # 'f', 't', or 'l'
                    if hasattr(l, smp) and getattr(l, smp) is not None and\
                        len(getattr(l, smp)) > 0:
                        #logging.info(l.willt_url_code)
                        logging.info(getattr(l, smp))
                        ao[abbr]['sh'] += 1
                        link_clicks = l.count_clicks()
                        ao[abbr]['cl'] += link_clicks
                        if userID:
                            users[abbr][userID]['sh'] += 1
                            users[abbr][userID]['cl'] += link_clicks
                        else:
                            lost += 1
                        if abbr == 'f':
                            ao[abbr]['re'] += len(getattr(user, 'fb_friends', []))
                        elif abbr == 't':
                            twitter_follower_count = getattr(user, 'twitter_follower_count', 0) 
                            # this returned as none sometimes when it's null
                            twitter_follower_count = 0 if twitter_follower_count\
                                is None else twitter_follower_count
                            ao[abbr]['re'] += twitter_follower_count
                        elif abbr == 'l':
                            ao[abbr]['re'] += len(getattr(user, 'linkedin_connected_users', []))
                    if hasattr(l, 'link_conversions'):
                            ao[abbr]['co'] += 1
                            if userID:
                                users[abbr][userID]['co'] += 1
                            order = ShopifyOrder.filter('campaign =', campaign)\
                                .filter('order_id =', l.link_conversions.order)
                            ao[abbr]['pr'] += order.subtotal_price

        user_list = sorted(users.iteritems(), lambda u: (u['co'], ['cl'], ['sh']))
        logging.info(user_list)
        #crate_campaign_analytics(None, None, None, ao['f'], ao['t']. ao['l'], 
        #logging.info(ao)
        #logging.info(users)
        #logging.info(lost)



    def get_results( self, total_clicks ) :
        """Get the results of this campaign, sorted by link count"""
        if total_clicks == 0:
            return [], ''
        
        #logging.info("total clicks for %s %d" % (self.title, total_clicks))
        #logging.info("links: %d" % self.links_.count())
        # Aggregate and nicen up the link data
        total_clicks = float( total_clicks )
        users = []
        ret   = []
        mixpanel_top = "platform.create_line_chart( 'graph_div', ["
        mixpanel_end = "], { 'mapping' : {" 
        for l in self.links_:
            clicks = l.count_clicks()
            
            #logging.info('Looking at Link: %s (%d)' % (l.willt_url_code, clicks))
            if clicks > 0 and l.user:
                #logging.info("Link %d has user: %s" % (clicks, l.user.get_attr('twitter_handle')) )

                if l.user.get_attr('twitter_handle') in users:
                    for foo in ret:
                        if foo['user']:
                            if foo['user'].get_attr('twitter_handle') == l.user.get_attr('twitter_handle'):
                                foo['clicks'] += clicks
                                foo['clicks_ratio'] += round( (float(clicks)/total_clicks)*100.0, 2)
                else:
                    users.append( l.user.get_attr('twitter_handle') )
                    
                    mixpanel_top += "'Clicks_%s_%s', " % (self.uuid, l.user.get_attr('twitter_handle'))
                    mixpanel_end += "'Clicks_%s_%s' : \"%s's Clickthroughs\", " % (self.uuid, l.user.get_attr('twitter_handle'), l.user.get_attr('twitter_handle'))
                    
                    ret.append( {'num' : 0, # placeholder since list isn't in order yet
                                 'user' : l.user,
                                 'link' : l,
                                 'kscore' : "<10" if l.user.get_attr('kscore') == "1.0" else l.user.get_attr('kscore'),
                                 'clicks' : clicks,
                                 'clicks_ratio' : round( (float(clicks)/total_clicks)*100.0, 2)
                                 } )
            elif clicks > 0 and not l.user:
                #logging.info("Link %s %d has NO user" % (l.willt_url_code, clicks) )
                ret.append( {'num' : 0,
                             'user' : None,
                             'kscore': '',
                             'clicks' : clicks,
                             'clicks_ratio' : round( (float(clicks)/total_clicks)*100.0, 2) } )
        
        # Now that the results are aggregated, SORT!
        lst = sorted(ret, key = lambda x: -x['clicks'] )
        
        # Now, let's be inefficient for a sec.
        for i in range(0, len(lst)):
            lst[i]['num'] = i+1
        
        mixpanel_end += "}, 'legend': false, 'cumulative' : true, 'xlabel' : 'Date', 'ylabel' : 'Counts', interval: 7} );"
        return lst, mixpanel_top+mixpanel_end
    
    def count_clicks( self ):
        # Get an updated value by putting this on a queue
        taskqueue.add( queue_name='campaign-ClicksCounter', 
                       url='/campaignClicksCounter', 
                       name= 'campaign_ClicksCounter_%s_%s' % (self.uuid, generate_uuid( 10 )),
                       params={'campaign_uuid' : self.uuid} )
        # Return an old cached value
        return self.cached_clicks_count
    
    def get_shares_count(self):
        """Count this campaigns sharded shares"""
        
        total = memcache.get(self.uuid+"ShareCounter")
        if total is None:
            total = 0
            for counter in ShareCounter.all().\
            filter('campaign_id =', self.uuid).fetch(15):
                total += counter.count
            memcache.add(key=self.uuid+"ShareCounter", value=total)
        return total
    
    def add_shares(self, num):
        """add num clicks to this campaign's share counter"""

        def txn():
            index = random.randint(0, NUM_SHARE_SHARDS-1)
            shard_name = self.uuid + str(index)
            counter = ShareCounter.get_by_key_name(shard_name)
            if counter is None:
                counter = ShareCounter(key_name=shard_name, 
                                       campaign_id=self.uuid)
            counter.count += num
            counter.put()

        db.run_in_transaction(txn)
        memcache.incr(self.uuid+"ShareCounter")

    def increment_shares(self):
        """Increment this link's click counter"""
        self.add_shares(1)

def get_campaign_by_id( id ):
    return Campaign.all().filter( 'uuid =', id ).get()

def get_campaign_by_shopify_store( name ):
    return Campaign.all().filter( 'product_name =', name ).get()

class ShareCounter(db.Model):
    """Sharded counter for link click-throughs"""

    campaign_id = db.StringProperty(indexed=True, required=True)
    count = db.IntegerProperty(indexed=False, required=True, default=0)


class CampaignAnalytics(Model):
    """Model containing aggregated analytics about a specific campaign
    
        The stats list properties are comma seperated lists of statistics, see their
        accompanying comments for more details but you should be able to just use the
        accessors"""

    uuid = db.StringProperty(indexed=True)
    scope = db.StringProperty() #week/month

    start_time = db.DateTimeProperty()
    end_time = db.DateTimeProperty()
    creation_time = db.DateTimeProperty(auto_now_add=True)

    # all stat lists are of the form: [shares, reach, clicks, conversion, profit]
    facebook_stats = db.ListProperty(str)
    twitter_stats = db.ListProperty(str)
    linkedin_stats = db.ListProperty(str)
    email_stats = db.ListProperty(str)

    # each user's stats are the 4 consecutive elements "medium_handle,conversions,clicks,shares"
    facebook_user_stats = db.ListProperty(str)
    twitter_user_stats = db.ListProperty(str)
    linkedin_user_stats = db.ListProperty(str)
    
    def __init__(self, *args, **kwargs):
        self._memcache_key = kwargs['uuid'] if 'uuid' in kwargs else None 
        super(CampaignAnalytics, self).__init__(*args, **kwargs)
    
    @staticmethod
    def _get_from_datastore(uuid):
        """Datastore retrieval using memcache_key"""
        return db.Query(CampaignAnalytics).filter('uuid =', uuid).get()


def create_campaign_analytics(scope, start_time, end_time, fb_stats=None,\
twitter_stats=None,linkedin_stats=None,users)
    """the _stats objects are of the form:
        [cl]icks, [co]nversions, [re]ach, [pr]ofit, [sh]are
        { cl: int, co: int, re: int, pr: int, sh: int }
        users list (ordered by influence)::
            [ { f : { handle: str, co: int, cl: int, sh: int }, 
              { t : ... } ]
        
        Returns: CampaignAnalytics object. See CampaignAnlytics model definition
                 for internal data representations
    """
    stats_lists = []
    fb_slist, twitter_slist, linkedin_slit = [map(getattr(stats, x),\
        ['sh', 're', 'cl', 'co', 'pr']) for stats in  [fb_stats, twitter_stats, linkedin_stats]]:
    logging.info(fb_slist)
    #fb_stats = map(getattr(fb_stats, x), ['sh', 're', 'cl', 'co', 'pr']) 
    #twitter_stats = map(fetat
            

def get_campaign_analytics_by_uuid(uuid, scope):
    return CampaignAnalytics.all().filter('uuid =', uuid).get()

