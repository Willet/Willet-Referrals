# ShopifyCampaign model
# models a client's sharing campaign

__all__ = [
    'ShopifyCampaign'
]

import hashlib, logging, random, urllib, urllib2, datetime

from decimal import *

from django.utils import simplejson as json
from google.appengine.api import memcache
from google.appengine.api import urlfetch
from google.appengine.api import taskqueue
from google.appengine.ext import db

from models.link import Link, get_active_links_by_campaign
from models.user import User
from models.model import Model
from util            import httplib2

from util.consts import *
from util.helpers import generate_uuid

NUM_SHARE_SHARDS = 15

class ShopifyCampaign(Model):
    """Model storing the data for a client's sharing campaign"""
    uuid          = db.StringProperty( indexed = True )
    created       = db.DateTimeProperty(auto_now_add=True)
    emailed_at_10 = db.BooleanProperty( default = False )
    client        = db.ReferenceProperty( db.Model, collection_name = 'shopify_campaigns' )
    
    cached_clicks_count = db.IntegerProperty( default = 0 )
    
    store_name    = db.StringProperty( indexed = False )
    store_url     = db.LinkProperty  ( indexed = True )
    store_token   = db.StringProperty( default = '' )
    
    # Default share text
    share_text    = db.StringProperty( indexed = False )

    analytics     = db.ReferenceProperty(db.Model, collection_name='scanalytics')

    # Defaults to None, only set if this ShopifyCampaign has been deleted
    old_client    = db.ReferenceProperty( db.Model, collection_name = 'deleted_shopify_campaigns' )

    # Store product img URLs and do something useful with them
    product_imgs  = db.StringListProperty( indexed = False )
    
    def __init__(self, *args, **kwargs):
        # Install yourself in the Shopify store
        install_webhooks( self )
        install_script_tags( self )

        self._memcache_key = kwargs['uuid'] if 'uuid' in kwargs else None 
        super(ShopifyCampaign, self).__init__(*args, **kwargs)
    
    @staticmethod
    def _get_from_datastore(uuid):
        """Datastore retrieval using memcache_key"""
        return db.Query(ShopifyCampaign).filter('uuid =', uuid).get()

    def validateSelf( self ):
        # Fetch product imgs
        get_product_imgs( self )

    def update( self, store_name, store_url, share_text ):
        """Update the campaign with new data"""
        self.store_name = store_name
        self.store_url  = store_url
        self.share_text = share_text
        
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
                            users[m][userID] = {'co': 0, 'cl': 0, 'sh': 0,
                            'pr': 0, 'uid': user.key()}

                for smp in ['facebook_share_id', 'tweet_id', 'linkedin_share_url']:
                    abbr = smp[0] # 'f', 't', or 'l'
                    if hasattr(l, smp) and getattr(l, smp) is not None and\
                        len(getattr(l, smp)) > 0:
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
                            order = ShopifyOrder.filter('campaign =', campaign)\
                                .filter('order_id =', l.link_conversions.order)
                            ao[abbr]['pr'] += order.subtotal_price
                            if userID:
                                users[abbr][userID]['co'] += 1
                                users[abbr][UserID]['pr'] += order.subtotal_price

        top_user_lists = { 'f': [], 't': [], 'l': [] }
        for k, v in top_user_lists.iteritems():
            top_user_lists[k] = sorted(users[k].iteritems(),
                                       key=lambda u: (u[1]['co'], u[1]['cl'], u[1]['sh']),
                                       reverse=True)
        create_campaign_analytics(self.uuid, scope_string, scope, datetime.datetime.today(),\
            ao['f'], ao['t'], ao['l'], ao['e'], top_user_lists)

    def get_reports_since(self, scope, t, count=None):
        """ Get the reports analytics for this campaign since 't'"""
        ca = get_analytics_report_since(self.uuid, scope, t, count)
        social_media_stats = []
        for c in ca:
            for s in ['facebook', 'twitter', 'linkedin', 'email']:
                stats = getattr(c, s+'_stats')
                sms = {}
                sms['shares'] = stats[0]
                sms['reach'] = stats[1]
                sms['clicks'] = stats[2]
                sms['name'] = s
                sms['conversions'] = stats[3]
                sms['profit'] = stats[4]

                users = []
                user_stats = map(lambda x: x.split(","), 
                    getattr(c, s+'_user_stats', ""))
                for u_stat_list in user_stats:
                    user = db.get(u_stat_list[0])
                    if user:
                        user.conversions = u_stat_list[1]
                        user.clicks = u_stat_list[2]
                        user.shares = u_stat_list[3]
                        user.profit = u_stat_list[4]
                        users.append(user)
                sms['users'] = users
                social_media_stats.append(sms)
        logging.info(social_media_stats)
        return(social_media_stats)
             

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

def get_shopify_campaign_by_id( id ):
    return ShopifyCampaign.all().filter( 'uuid =', id ).get()

def get_shopify_campaign_by_url( url ):
    logging.info("Looking for %s" % url )
    return ShopifyCampaign.all().filter( 'store_url =', url ).get()

##### SHopify API Calls
def install_webhooks( campaign ):
    url      = '%s/admin/webhooks.json' % ( campaign.store_url )
    username = SHOPIFY_API_KEY
    password = hashlib.md5(SHOPIFY_API_SHARED_SECRET + campaign.store_token).hexdigest()
    header   = {'content-type':'application/json'}
    h        = httplib2.Http()
    
    # Auth the http lib
    h.add_credentials( username, password )
    
    # Install the "Order Creation" webhook
    data = { "webhook": { "address": "%s/shopify/webhook/order?store_id=%s" % (URL, campaign.uuid), "format": "json", "topic": "orders/create" } }
    logging.info("POSTING to %s %r " % (url, data) )
    resp, content = h.request(url, "POST", body=json.dumps(data), headers=header)
    logging.info('%r %r' % (resp, content))

    # Install the "App Uninstall" webhook
    data = { "webhook": { "address": "%s/shopify/webhook/uninstalled" % URL, "format": "json", "topic": "app/uninstalled" } }
    logging.info("POSTING to %s %r " % (url, data) )
    resp, content = h.request(url, "POST", body=json.dumps(data), headers=header)
    logging.info('%r %r' % (resp, content))
    
def install_script_tags( campaign ):
    url      = '%s/admin/script_tags.json' % ( campaign.store_url )
    username = SHOPIFY_API_KEY
    password = hashlib.md5(SHOPIFY_API_SHARED_SECRET + campaign.store_token).hexdigest()
    header   = {'content-type':'application/json'}
    h        = httplib2.Http()
    
    h.add_credentials( username, password )

    # Install the referral plugin on confirmation screen
    data = { "script_tag": { "src": "https://social-referral.appspot.com/shopify/static/js/referral.js", "event": "onload" } }      

    logging.info("POSTING to %s %r " % (url, data) )
    resp, content = h.request(url, "POST", body=json.dumps(data), headers=header)
    logging.info('%r %r' % (resp, content))

    # Install jquery cookies
    data = { "script_tag": { "src": "http://social-referral.appspot.com/shopify/static/js/jquery.cookie.js", "event": "onload" } }      
    
    logging.info("POSTING to %s %r " % (url, data) )
    resp, content = h.request(url, "POST", body=json.dumps(data), headers=header)
    logging.info('%r %r' % (resp, content))

    # Install the top_bar JS 
    data = { "script_tag": { "src": "http://social-referral.appspot.com/shopify/shopify/load/bar?store_id=%s" % (campaign.uuid), "event": "onload" } }      
    
    logging.info("POSTING to %s %r " % (url, data) )
    resp, content = h.request(url, "POST", body=json.dumps(data), headers=header)
    logging.info('%r %r' % (resp, content))


def get_product_imgs( campaign ):
    url = '%s/admin/products.json' % ( campaign.store_url )
    username = SHOPIFY_API_KEY
    password = hashlib.md5(SHOPIFY_API_SHARED_SECRET + campaign.store_token).hexdigest()

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
                    campaign.product_imgs.append( img )

