#!/usr/bin/python

# The App Model
# A parent class for all social 'apps'
# ie. Referral, 'Should I buy this?', etc

__author__      = "Willet, Inc."
__copyright__   = "Copyright 2011, Willet, Inc"

import hashlib, logging, random, urllib2, datetime

from decimal              import *
from django.utils         import simplejson as json
from google.appengine.api import memcache
from google.appengine.api import urlfetch
from google.appengine.api import taskqueue
from google.appengine.ext import db
from google.appengine.ext.db import polymodel

from apps.link.models     import Link, get_link_by_willt_code 
from apps.order.models    import Order
from apps.user.models     import User
from apps.user_analytics.models import UserAnalytics, UserAnalyticsServiceStats

from util.consts          import *
from util.helpers         import generate_uuid
from util.helpers         import url 
from util.model           import Model

NUM_SHARE_SHARDS = 15

class App(Model, polymodel.PolyModel):
    # Unique identifier for memcache and DB key
    uuid            = db.StringProperty( indexed = True )
    
    # Datetime when this model was put into the DB
    created         = db.DateTimeProperty( auto_now_add=True )
    
    # Person who created/installed this App
    client          = db.ReferenceProperty( db.Model, collection_name = 'apps' )
    
    # Defaults to None, only set if this App has been deleted
    old_client      = db.ReferenceProperty( db.Model, collection_name = 'deleted_apps' )
    
    # Analytics for this App
    analytics       = db.ReferenceProperty( db.Model, collection_name = "APPS" )
    
    # For Apps that use a click counter, this is the cached amount
    cached_clicks_count = db.IntegerProperty( default = 0 )
    
    def __init__(self, *args, **kwargs):
        self._memcache_key = kwargs['uuid'] if 'uuid' in kwargs else None 
        super(App, self).__init__(*args, **kwargs)
    
    @staticmethod
    def _get_from_datastore(uuid):
        """Datastore retrieval using memcache_key"""
        return App.all().filter('uuid =', uuid).get()

    def validateSelf( self ):
        # Subclasses should override this
        return

    def handleLinkClick( self ):
        # Subclasses must override this
        logging.error("THIS FCN SHOULD NEVER GET CALLED. FIX ME.")
        raise Exception("THIS FCN SHOULD NEVER GET CALLED. SUBCLASS ME!")

    def delete( self ):
        self.old_client = self.client
        self.client     = None
        self.put()
    
    def storeAnalyticsDatum( self, event, user, target ):
        if 'social-referral.appspot.com' not in URL:
            return

        if not user.is_admin():
            logging.info("Queuing up task to store '%s' to Mixpanel." % event )

            taskqueue.add(
                queue_name = 'mixpanel',
                url = url('SendActionToMixpanel'), 
                params = {
                    'event'     : event, 
                    'target_url': target,
                    
                    'app'       : self.uuid,
                    'client'    : self.client.email,
                    
                    'user'      : user.get_name_or_handle(),
                    'user_uuid' : user.uuid,
                }
            )

    def compute_analytics(self, scope):
        """Update the AppAnalytics model for this uuid 
            with latest available data""" 

        app = get_app_by_id(self.uuid)
        service_keys = ['facebook_share_id', 'tweet_id', 'linkedin_share_url']
        
        # interpret the scope to a date
        scope_string = scope
        scope = datetime.datetime.today() - datetime.timedelta(30) if scope == 'month'\
            else datetime.datetime.today()-datetime.timedelta(7)

        # twitter, facebook, linkedin
        app_analytics, users = {}, {}
        lost = 0
        for smp in ['t', 'f', 'l', 'e']:
            # [cl]icks, [co]nversions, [sh]ares, [re]ach, [pr]ofit
            app_analytics[smp] = {'cl': 0, 'co': 0, 'sh': 0, 're': 0, 'pr': 0} 
            users[smp] = {}
        
        if app:
            # this filter should work but doesn't for some reason
            links = app.links_ # .filter('creation_time >=', scope)
            for l in links: #[l for l in app.links_ if hasattr(l, 'user')]:
                # by default assume a link has not been shared, abbr is false
                abbr = False
                if l.creation_time < scope:
                    logging.info("Skipping: " + str(l.creation_time))
                    continue

                user = getattr(l, 'user', None)
                userID = getattr(user, 'uuid', None)# if hasattr(l, 'user') else None
                
                for smp in service_keys:
                    if hasattr(l, smp) and getattr(l, smp) is not None and\
                        len(getattr(l, smp)) > 0:
                        # this link was shared on this service
                        abbr = smp[0] # 'f', 't', or 'l'
                
                if abbr == False:
                    # we didn't detect it shared, double check for email
                    if hasattr(l, 'email_sent'):
                        if getattr(l, 'email_sent') == True:
                            # woohoo, it was shared!
                            abbr = 'e'
                        else:
                            continue
                    else:
                        continue

                if userID:
                    #users[abbr][userID] = {}
                    #for service in ['t', 'f', 'l', 'e']: #twitter, facebook, linkedin
                        # [co]nversions, [cl]icks, [sh]are
                    if not users[abbr].has_key(userID):
                        users[abbr][userID] = {
                            'co': 0,
                            'cl': 0,
                            'sh': 0,
                            'pr': 0,
                            'uid': user.key()
                        }
                
                logging.info('got link: %s\nuser: %s\nservice: %s' % (
                    l,
                    user,
                    abbr
                ))

                # okay if we got here this link was shared
                app_analytics[abbr]['sh'] += 1
                link_clicks = l.count_clicks()
                app_analytics[abbr]['cl'] += link_clicks
                if userID:
                    users[abbr][userID]['sh'] += 1
                    users[abbr][userID]['cl'] += link_clicks
                else:
                    lost += 1
                app_analytics[abbr]['re'] += user.get_reach(service=abbr) 
                #if abbr == 'f':
                #    app_analytics[abbr]['re'] += len(getattr(user, 'fb_friends', []))
                #elif abbr == 't':
                #    twitter_follower_count = getattr(user, 'twitter_follower_count', 0) 
                #    # this returned as none sometimes when it's null
                #    twitter_follower_count = 0 if twitter_follower_count\
                #        is None else twitter_follower_count
                #    app_analytics[abbr]['re'] += twitter_follower_count
                #elif abbr == 'l':
                #    app_analytics[abbr]['re'] += len(getattr(user, 'linkedin_connected_users', []))
                if hasattr(l, 'link_conversions'):
                    app_analytics[abbr]['co'] += 1
                    order_id = l.link_conversions.order

                    # ugly hack to make sure there is an order_id
                    if type(order_id) == type(str()):
                        order = Order.all().filter('app =', app)\
                                    .filter('order_id =', order_id)
                        for o in order:
                            if hasattr(o, 'subtotal_price'):
                                subtotal_price += o.subtotal_price
                    else:
                        subtotal_price = 0

                    # hack to make sure there is a subtotal price
                    # and cuz we can't get the sbtl_price from a queryset
                    
                    app_analytics[abbr]['pr'] += subtotal_price
                    if userID:
                        users[abbr][userID]['co'] += 1
                        users[abbr][userID]['pr'] += subtotal_price

        top_user_lists = {
            'f': [],
            't': [],
            'l': [],
            'e': [] 
        }
        for k, v in top_user_lists.iteritems():
            top_user_lists[k] = sorted (
                users[k].iteritems(),
                key=lambda u: (u[1]['co'], u[1]['cl'], u[1]['sh']),
                reverse=True
            )

        create_app_analytics(
            self.uuid,
            scope_string,
            scope,
            datetime.datetime.today(),
            app_analytics['f'],
            app_analytics['t'],
            app_analytics['l'],
            app_analytics['e'],
            top_user_lists
        )

    def get_reports_since(self, scope, t, count=None):
        """ Get the reports analytics for this app since 't'"""
        ca = get_analytics_report_since(self.uuid, scope, t, count)
        social_media_stats = []
        totals = {
            'shares': 0,
            'reach': 0,
            'clicks': 0,
            'conversions': 0,
            'profit': 0
        }
        for c in ca:
            #for s in ['facebook', 'twitter', 'linkedin', 'email']:
            for s in ['facebook', 'twitter', 'email']:
                stats = getattr(c, s+'_stats')
                sms = {}
                sms['name'] = s

                sms['shares'] = stats[0]
                totals['shares'] += stats[0] 

                sms['reach'] = stats[1]
                totals['reach'] += stats[1]

                sms['clicks'] = stats[2]
                totals['clicks'] += stats[2]


                sms['conversions'] = stats[3]
                totals['conversions'] += stats[3]

                sms['profit'] = stats[4]
                totals['profit'] += stats[4]

                users = []
                user_stats = map(lambda x: x.split(","), getattr(c, s+'_user_stats', ""))
                for u_stat_list in user_stats:
                    user = db.get(u_stat_list[0])
                    if user:
                        user.conversions = u_stat_list[1]
                        user.clicks = u_stat_list[2]
                        user.shares = u_stat_list[3]
                        if len(u_stat_list) > 4:
                            user.profit = u_stat_list[4]
                        else:
                            user.profit = 0
                        el = {}
                        el['conversions'] = u_stat_list[1]
                        el['clicks'] = u_stat_list[2]
                        el['shares'] = u_stat_list[3]
                        el['profit'] = user.profit 
                        el['reach'] = user.get_reach(service=s)
                        el['handle'] = user.get_handle(service=s)
                        el['uuid'] = user.uuid
                        el['user'] = user
                        users.append(el)
                sms['users'] = users
                social_media_stats.append(sms)
        logging.info(social_media_stats)
        return social_media_stats, totals
             
    def get_results( self, total_clicks ) :
        """Get the results of this app, sorted by link count"""
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
        taskqueue.add(
            queue_name = 'app-ClicksCounter', 
            url = '/a/appClicksCounter', 
            name = 'app_ClicksCounter_%s_%s' % (
                self.uuid,
                generate_uuid( 10 )),
            params = {
                'app_uuid' : self.uuid
            }
        )
        # Return an old cached value
        return self.cached_clicks_count
    
    def get_shares_count(self):
        """Count this apps sharded shares"""
        total = memcache.get(self.uuid+"ShareCounter")
        if total is None:
            total = 0
            for counter in ShareCounter.all().\
            filter('app_id =', self.uuid).fetch(15):
                total += counter.count
            memcache.add(key=self.uuid+"ShareCounter", value=total)
        return total
    
    def add_shares(self, num):
        """add num clicks to this app's share counter"""
        def txn():
            index = random.randint(0, NUM_SHARE_SHARDS-1)
            shard_name = self.uuid + str(index)
            counter = ShareCounter.get_by_key_name(shard_name)
            if counter is None:
                counter = ShareCounter(key_name=shard_name, 
                                       app_id=self.uuid)
            counter.count += num
            counter.put()

        db.run_in_transaction(txn)
        memcache.incr(self.uuid+"ShareCounter")

    def increment_shares(self):
        """Increment this link's click counter"""
        self.add_shares(1)

def get_app_by_id( id ):
    return App.all().filter( 'uuid =', id ).get()

## -----------------------------------------------------------------------------
## -----------------------------------------------------------------------------
## -----------------------------------------------------------------------------
class ShareCounter(db.Model):
    """Sharded counter for link click-throughs"""

    app_id = db.StringProperty(indexed=True, required=True)
    count  = db.IntegerProperty(indexed=False, required=True, default=0)

## -----------------------------------------------------------------------------
## -----------------------------------------------------------------------------
## -----------------------------------------------------------------------------
class AppAnalytics(Model):
    """Model containing aggregated analytics about a specific app
    
        The stats list properties are comma seperated lists of statistics, see their
        accompanying comments for more details but you should be able to just use the
        accessors"""

    app_uuid=db.StringProperty(indexed=True)
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
    email_user_stats    = db.ListProperty(str)
    
    def __init__(self, *args, **kwargs):
        self._memcache_key = kwargs['uuid'] if 'uuid' in kwargs else None 
        super(AppAnalytics, self).__init__(*args, **kwargs)
    
    @staticmethod
    def _get_from_datastore(uuid):
        """Datastore retrieval using memcache_key"""
        return db.Query(AppAnalytics).filter('uuid =', uuid).get()


def create_app_analytics(app_uuid, scope, start_time, end_time,\
fb_stats=None, twitter_stats=None,linkedin_stats=None,email_stats=None,users=None):
    """the _stats objects are of the form:
        { cl: int, co: int, re: int, pr: int, sh: int }
        [cl]icks, [co]nversions, [re]ach, [pr]ofit, [sh]are

        users list (ordered by influence)::
            [ { f : { handle: str, co: int, cl: int, sh: int, pr: int }, 
              { t : ... } ]
        
        Returns: AppAnalytics object. See AppAnlytics model definition
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
        map(lambda attr: str(user[1][attr]), ['uid', 'co', 'cl', 'sh', 'pr'])
    fcsv = lambda x: ",".join(x)
    fb_user_stats = map(fcsv, map(user_stats_obj_to_list, users['f']))
    tw_user_stats = map(fcsv, map(user_stats_obj_to_list, users['t']))
    li_user_stats = map(fcsv, map(user_stats_obj_to_list, users['l']))
    e_user_stats = map(fcsv, map(user_stats_obj_to_list, users['e']))
    logging.info(tw_user_stats)
    ca = AppAnalytics(uuid=generate_uuid(16),
        app_uuid=app_uuid,
        scope=scope,
        start_time=start_time,
        end_time=end_time,
        facebook_stats=fb_stats,
        twitter_stats=twitter_stats,
        linkedin_stats=linkedin_stats,
        email_stats=email_stats,
        facebook_user_stats=fb_user_stats,
        twitter_user_stats=tw_user_stats,
        linkedin_user_stats=li_user_stats,
        email_user_stats = e_user_stats
    )
    ca.save()
    
    return ca

def get_app_analytics_by_uuid(uuid, scope):
    return AppAnalytics.all().filter('uuid =', uuid).get()

def get_analytics_report_since(app_uuid, scope, t, count=None):
    logging.info("Looking up report for %s since %s" % (app_uuid, t))
    ca = AppAnalytics.all().filter('app_uuid =', app_uuid).filter('scope =', scope)#\
        #.filter('start_time >=', t)
    if count is not None and count > 0:
        ca = ca.fetch(count)
        #return ca.fetch(count)
    for c in ca:
        logging.info(c.start_time)
    return ca


## -----------------------------------------------------------------------------
## -----------------------------------------------------------------------------
## -----------------------------------------------------------------------------
class Conversion(Model):
    """Model storing conversion data"""
    uuid     = db.StringProperty( indexed = True )
    created  = db.DateTimeProperty(auto_now_add=True)
    link     = db.ReferenceProperty( db.Model, collection_name="link_conversions" )
    referrer = db.ReferenceProperty( db.Model, collection_name="users_referrals" )
    referree = db.ReferenceProperty( db.Model, default = None, collection_name="users_been_referred" )
    referree_uid = db.StringProperty()
    app      = db.ReferenceProperty( db.Model, collection_name="app_conversions" )
    order    = db.StringProperty()

    def __init__(self, *args, **kwargs):
        self._memcache_key = kwargs['uuid'] if 'uuid' in kwargs else None 
        super(Conversion, self).__init__(*args, **kwargs)
    
    @staticmethod
    def _get_from_dataapp( uuid ):
        """Dataapp retrieval using memcache_key"""
        return db.Query(Conversion).filter('uuid =', uuid).get()

def create_conversion( link, app, referree_uid, referree, order_num ):
    uuid = generate_uuid(16)
    
    c = Conversion( key_name     = uuid,
                    uuid         = uuid,
                    link         = link,
                    referrer     = link.user,
                    referree     = referree,
                    referree_uid = referree_uid,
                    app          = app,
                    order        = order_num )
    c.put()

    return c # return incase the caller wants it
