# Campaign model
# models a client's sharing campaign

__all__ = [
    'Campaign'
]

import logging, random

from datetime import datetime
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
    uuid        = db.StringProperty( indexed = True )
    title       = db.StringProperty( indexed = False )
    button_text = db.StringProperty( indexed = False )
    button_subtext = db.StringProperty( indexed = False )
    share_text  = db.StringProperty( indexed = False )
    target_url  = db.LinkProperty( indexed = False )
    redirect_url = db.LinkProperty( required = False, default = None, indexed = False )
    created     = db.DateTimeProperty(auto_now_add=True)
    emailed_at_10 = db.BooleanProperty( default = False )
    client      = db.ReferenceProperty( db.Model, collection_name = 'campaigns' )
    cached_clicks_count = db.IntegerProperty( default = 0 )

    # Defaults to None, only set if this Campaign has been deleted
    old_client  = db.ReferenceProperty( db.Model, collection_name = 'deleted_campaigns' )
    
    def __init__(self, *args, **kwargs):
        if kwargs.get('redirect_url', None) == 'http://':
            kwargs['redirect_url'] = None
        self._memcache_key = kwargs['uuid'] if 'uuid' in kwargs else None 
        super(Campaign, self).__init__(*args, **kwargs)
    
    @staticmethod
    def _get_from_datastore(uuid):
        """Datastore retrieval using memcache_key"""
        return db.Query(Campaign).filter('uuid =', uuid).get()
    
    def update( self, title, button_text, button_subtext, share_text, target_url, redirect_url ):
        if redirect_url == 'http://':
            redirect_url = None
        
        """Update the campaign with new data"""
        self.title       = title
        self.button_text = button_text
        self.button_subtext = button_subtext
        self.share_text  = share_text
        self.target_url  = target_url
        self.redirect_url = redirect_url
        self.put()
    
    def delete( self ):
        self.old_client = self.client
        self.client     = None
        self.put()
        
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
                #logging.info("Link %d has user: %s" % (clicks, l.user.twitter_handle) )

                if l.user.twitter_handle in users:
                    for foo in ret:
                        if foo['user']:
                            if foo['user'].twitter_handle == l.user.twitter_handle:
                                foo['clicks'] += clicks
                                foo['clicks_ratio'] += round( (float(clicks)/total_clicks)*100.0, 2)
                else:
                    users.append( l.user.twitter_handle )
                    
                    mixpanel_top += "'Clicks_%s_%s', " % (self.uuid, l.user.twitter_handle)
                    mixpanel_end += "'Clicks_%s_%s' : \"%s's Clickthroughs\", " % (self.uuid, l.user.twitter_handle, l.user.twitter_handle)
                    
                    ret.append( {'num' : 0, # placeholder since list isn't in order yet
                                 'user' : l.user,
                                 'link' : l,
                                 'kscore' : "<10" if l.user.kscore < 10 else int(round(l.user.kscore)),
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


class ShareCounter(db.Model):
    """Sharded counter for link click-throughs"""

    campaign_id = db.StringProperty(indexed=True, required=True)
    count = db.IntegerProperty(indexed=False, required=True, default=0)

