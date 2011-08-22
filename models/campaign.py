# Campaign model
# models a client's sharing campaign

__all__ = [
    'Campaign'
]

import hashlib, logging, random, urllib2, datetime

from decimal import *

from django.utils import simplejson as json
from google.appengine.api import memcache
from google.appengine.api import urlfetch
from google.appengine.api import taskqueue
from google.appengine.ext import db

from models.link import Link, get_active_links_by_campaign
from models.user import User
from models.model import Model
from util.consts import *
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

    shopify_token = db.StringProperty( default = '' )
    # Urls for 3 random products - hacked for now
    shopify_productA_img = db.StringProperty( default = '' )
    shopify_productB_img = db.StringProperty( default = '' )
    shopify_productC_img = db.StringProperty( default = '' )
    
    def __init__(self, *args, **kwargs):
        self._memcache_key = kwargs['uuid'] if 'uuid' in kwargs else None 
        super(Campaign, self).__init__(*args, **kwargs)
    
    @staticmethod
    def _get_from_datastore(uuid):
        """Datastore retrieval using memcache_key"""
        return db.Query(Campaign).filter('uuid =', uuid).get()

    def validateSelf( self ):
        url = '%s/admin/products.json' % ( self.target_url )
        username = SHOPIFY_API_KEY
        password = hashlib.md5(SHOPIFY_API_SHARED_SECRET + self.shopify_token).hexdigest()

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
        details  = json.loads( result.read() ) #['orders'] # Fetch the order
        products = details['products']

        for p in products:
            for k, v in p.iteritems():
                if 'images' in k:
                    if len(v) != 0:
                        img = v[0]['src'].split('?')[0]
                        logging.info('%s %s' % (self.shopify_productA_img, img))
                        if self.shopify_productA_img == '':
                            self.shopify_productA_img = img
                        elif self.shopify_productB_img == '' and img != self.shopify_productA_img:
                            self.shopify_productB_img = img
                        elif self.shopify_productC_img == '' and img  != self.shopify_productA_img and img != self.shopify_productB_img:
                            self.shopify_productC_img = img
                            return
                        else:
                            return
    
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
        scope_string = scope
        scope = datetime.datetime.today() - datetime.timedelta(30) if scope == 'month'\
            else datetime.datetime.today()-datetime.timedelta(7)

        # twitter, facebook, linkedin
        ao, users = {}, {}
        lost = 0
        for smp in ['t', 'f', 'l', 'e']:
            # [cl]icks, [co]nversions, [sh]ares, [re]ach, [pr]ofit
            ao[smp] = {'cl': 0, 'co': 0, 'sh': 0, 're': 0, 'pr': 0} 
            users[smp] = {}

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
                if userID:
                    #users[abbr][userID] = {}
                    for m in ['t', 'f', 'l']: #twitter, facebook, linkedin
                        # [co]nversions, [cl]icks, [sh]are
                        if not users[m].has_key(userID):
                            users[m][userID] = {'co': 0, 'cl': 0, 'sh': 0, 'uid': userID}

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

        top_user_lists = { 'f': [], 't': [], 'l': [] }
        for k, v in top_user_lists.iteritems():
            logging.info(users[k].items())
            top_user_lists[k] = sorted(users[k].iteritems(),
                                       key=lambda u: (u[1]['co'], u[1]['cl'], u[1]['sh']),
                                       reverse=True)
        logging.info(top_user_lists)
        create_campaign_analytics(self.uuid, scope_string, scope, datetime.datetime.today(),\
            ao['f'], ao['t'], ao['l'], ao['e'], top_user_lists)

    def get_reports_since(self, scope, t, count=None):
        """ Get the reports analytics for this campaign since 't'"""
        ca = get_analytics_report_since(self.uuid, scope, t, count)
        logging.info(ca)
        social_media_stats = []
        for c in ca:
            for s in ['facebook', 'twitter', 'linkedin', 'email']:
                stats = c.getattr(s+'_stats')
                sms = {}
                sms['shares'] = stats[0]
                sms['reach'] = stats[1]
                sms['clicks'] = stats[2]
                sms['name'] = s
                sms['conversions'] = stats[3]
                sms['profit'] = stats[4]

                users = {}
                user_stats = filter(lambda x: x, c.getattr(s+'_user_stats'))
                # separate the users by splitting the list into 
                x = 0
                while x < len(user_stats):
                    user = db.get(user_stats[x])
                    if user:
                        user.conversions = user_stats[x+1]
                        user.clicks = user_stats[x+2]
                        user.shares = user_stats[x+3]
                        x += 4
                        users.append(user)
                sms['users'] = users
                social_media_stats.append(sms)
            logging.info(social_media_stats)
             

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
    scope = db.StringProperty(indexed=True) #week/month

    start_time = db.DateTimeProperty(indexed=True)
    end_time = db.DateTimeProperty()
    creation_time = db.DateTimeProperty(auto_now_add=True)

    # all stat lists are of the form: [shares, reach, clicks, conversion, profit]
    facebook_stats = db.ListProperty(int)
    twitter_stats = db.ListProperty(int)
    linkedin_stats = db.ListProperty(int)
    email_stats = db.ListProperty(int)

    # each user's stats are the 4 consecutive elements "uuid,conversions,clicks,shares"
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


def create_campaign_analytics(campaign_uuid, scope, start_time, end_time,\
fb_stats=None, twitter_stats=None,linkedin_stats=None,email_stats=None,users=None):
    """the _stats objects are of the form:
        { cl: int, co: int, re: int, pr: int, sh: int }
        [cl]icks, [co]nversions, [re]ach, [pr]ofit, [sh]are

        users list (ordered by influence)::
            [ { f : { handle: str, co: int, cl: int, sh: int }, 
              { t : ... } ]
        
        Returns: CampaignAnalytics object. See CampaignAnlytics model definition
                 for internal data representations
    """
    # provider is an object
    logging.info(fb_stats)
    stats_obj_to_list = lambda prov:\
        map(lambda attr: prov[attr], ['sh', 're', 'cl', 'co', 'pr'])
    fb_stats, twitter_stats, linkedin_stats, email_stats = map(stats_obj_to_list,\
        [fb_stats, twitter_stats, linkedin_stats, email_stats])
    # user is a tuple
    user_stats_obj_to_list = lambda user:\
        map(lambda attr: str(user[1][attr]), ['uid', 'co', 'cl', 'sh'])
    fcsv = lambda x: ",".join(x)
    fb_user_stats = map(fcsv, map(user_stats_obj_to_list, users['f']))
    tw_user_stats = map(fcsv, map(user_stats_obj_to_list, users['t']))
    li_user_stats = map(fcsv, map(user_stats_obj_to_list, users['l']))
    logging.info(tw_user_stats)
    ca = CampaignAnalytics(uuid=generate_uuid(16),
        scope=scope,
        start_time=start_time,
        end_time=end_time,
        facebook_stats=fb_stats,
        twitter_stats=twitter_stats,
        linkedin_stats=linkedin_stats,
        email_stats=email_stats,
        facebook_user_stats=fb_user_stats,
        twitter_user_stats=tw_user_stats,
        linkedin_user_stats=li_user_stats
    )
    ca.save()
    
    return ca


def get_campaign_analytics_by_uuid(uuid, scope):
    return CampaignAnalytics.all().filter('uuid =', uuid).get()


def get_analytics_report_since(uuid, scope, t, count=None):
    ca = CampaignAnalytics.all().filter('uuid =', uuid).filter('scope =', scope)\
        .filter('start_time >=', t)
    if count is not None and count > 0:
        return ca.get(count)
    return ca
         

