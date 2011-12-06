#!/usr/env/python

import logging
import datetime

from mapreduce import operation as op
from mapreduce import control
from google.appengine.ext import webapp
from google.appengine.ext import db

from apps.analytics_backend.models import AppAnalyticsHourSlice
from apps.analytics_backend.models import AppAnalyticsDaySlice
from apps.analytics_backend.models import GlobalAnalyticsHourSlice
from apps.analytics_backend.models import GlobalAnalyticsDaySlice
from apps.analytics_backend.models import actions_to_count
from apps.action.models import Action
#from apps.app.models import App

#####
# These classes are CRON jobs that initiate the objects need for map reduce
#####

def ensure_hourly_slices(app):
    """Makes sure the hourly app slices are there"""
    today = datetime.datetime.today()
    hours = range(24)
    put_list = []
    for hour in hours:
        val = today - datetime.timedelta(hours=hour)
        logging.error('Creating hour')
        ahs, created = AppAnalyticsHourSlice.get_or_create(app_=app, start=val, 
                put=False)
        if created:
            logging.error('put: %s' % ahs)
            yield op.db.Put(ahs)     

def build_hourly_stats(time_slice):
    """this is our mapper"""
    start = time_slice.start
    end = time_slice.end
    app_ = time_slice.app_
    logging.debug("Counting %d actions from %s to %s" % (
        len(actions_to_count), start, end))
    for action in actions_to_count:
        logging.debug("Counting for action: %s" % action)
        value = count_action(app_, action, start, end)
        setattr(time_slice, action, value)

    yield op.db.Put(time_slice)

def count_action(app_, action, start, end):
    """Returns an Integer count for this action in the time period
    Note that with limit=None in the count() this operation will try to count
    all actions, but if it fails, it will time out."""
    return Action.all()\
        .filter('app_ =', app_)\
        .filter('class =', action)\
        .filter('created >=', start)\
        .filter('created <=', end)\
        .count(limit=None)

def ensure_daily_slices(app):
    """Makes sure the daily app slices are there"""
    today = datetime.datetime.combine(datetime.date.today(), datetime.time())
    days = range(7)
    put_list = []
    for day in days:
        val = today - datetime.timedelta(days=day)
        ahs, created = AppAnalyticsDaySlice.get_or_create(app_=app, start=val, 
                put=False)
        if created:
            yield op.db.Put(ahs)      

def build_daily_stats(time_slice):
    """this is our mapper"""
    start = time_slice.start
    end = time_slice.end
    app_ = time_slice.app_

    for action in actions_to_count:
        time_slice.default(action)

    hour_slices = AppAnalyticsDaySlice.all()\
            .filter('app_ =', app_)\
            .filter('start >=', start)\
            .filter('end <', end)

    for hour_slice in hour_slices:
        for action in actions_to_count:
            hour_value = hour_slice.get_attr(action)
            time_slice.increment(action, hour_value)

    yield op.db.Put(time_slice)

def build_global_hourly_stats(global_slice):
    start = global_slice.start
    end = global_slice.end

    #for action in actions_to_count:
    #    global_slice.default(action)

    hour_slices = AppAnalyticsHourSlice.all()\
            .filter('start >=', start)\
            .filter('end <', end)
    action_first_run = []

    for hour_slice in hour_slices:
        for action in actions_to_count:
            if action not in action_first_run:
                global_slice.default(action)
                action_first_run.append(action)
            global_slice.increment(action, hour_slice.get_attr(action))
    yield op.db.put(global_slice)

def build_global_daily_stats(global_slice):
    start = global_slice.start
    end = global_slice.end

    #for action in actions_to_count:
    #    global_slice.default(action)

    hour_slices = GlobalAnalyticsHourSlice.all()\
            .filter('start >=', start)\
            .filter('end <', end)
    action_first_run = []

    for hour_slice in hour_slices:
        for action in actions_to_count:
            if action not in action_first_run:
                global_slice.default(action)
                action_first_run.append(action)
            global_slice.increment(action, hour_slice.get_attr(action))
    yield op.db.put(global_slice)

class TimeSlices(webapp.RequestHandler):
    def get(self, action, scope):
        e_base = 'apps.analytics_backend.models.%s'
        f_base = 'apps.analytics_backend.processes.%s'
        options = {
            'ensure': {
                'hour':{
                    'mr': {
                        'name': 'Create Hourly Analytics Models',
                        'func': f_base % 'ensure_hourly_slices',
                        'entity': 'apps.sibt.shopify.models.SIBTShopify'
                    } 
                },
                'day': {
                    'mr': {
                        'name': 'Create Daily Analytics Models',
                        'func': f_base % 'ensure_daily_slices',
                        'entity': 'apps.sibt.shopify.models.SIBTShopify'
                    }
                },
                'hour_global': {
                    'scope_range': range(24),
                    'today': datetime.datetime.combine(datetime.date.today(), datetime.time()),
                    'td': lambda t: datetime.timedelta(hours=t),
                    'cls': GlobalAnalyticsHourSlice,
                },
                'day_global': {
                    'scope_range': range(7),
                    'today': datetime.datetime.combine(datetime.date.today(), datetime.time()),
                    'td': lambda t: datetime.timedelta(days=t),
                    'cls': GlobalAnalyticsDaySlice,
                }
            }, 
            'run': {
                'hour': {
                    'name': 'Run Hourly Analytics',
                    'func': f_base % 'build_hourly_stats',
                    'entity': e_base % 'AppAnalyticsHourSlice'
                },
                'day': {
                    'name': 'Run Daily Analytics',
                    'func': f_base % 'build_daily_stats',
                    'entity': e_base % 'AppAnalyticsDaySlice'
                },
                'hour_global': {
                    'name': 'Run GLOBAL Hourly Analytics',
                    'func': f_base % 'build_global_hourly_stats',
                    'entity': e_base % 'GlobalAnalyticsHourSlice'
                },
                'day_global': {
                    'name': 'Run GLOBAL Daily Analytics',
                    'func': f_base % 'build_global_daily_stats',
                    'entity': e_base % 'GlobalAnalyticsDailySlice'
                },
            }
        }
        oas = options[action][scope]
        if action == 'ensure':
            if 'mr' not in oas:
                today = oas['today']
                scope_range = oas['scope_range']
                created_list = []
                for period in scope_range:
                    val = today - oas['td'](period)
                    entity, created = oas['cls'].get_or_create(start=val, put=False)
                    if created:
                        created_list.append(entity)
                db.put(created_list)
                self.response.out.write('Put: %s' % len(created_list))
                return
            else:
                mr = oas['mr']
        else:
            mr = options[action][scope]
        mapreduce_id = control.start_map(
            mr['name'],
            mr['func'],
            'mapreduce.input_readers.DatastoreInputReader', {
                'entity_kind': mr['entity'],
            },
            shard_count=10
        )
        self.response.out.write("started mr: %s" % mapreduce_id)

#class EnsureGlobalHourlySlices(webapp.RequestHandler):
#    def get(self):
#        today = datetime.datetime.today()
#        hours = range(24)
#        created_list = []
#        for hour in hours:
#            val = today - datetime.timedelta(hours=hour)
#            gats, created = GlobalAnalyticsHourSlice.get_or_create(start=val, 
#                    put=False) 
#            if created:
#                created_list.append(gats)
#        db.put(created_list)

#class EnsureGlobalDaySlices(webapp.RequestHandler):
#    def get(self):
#        today = datetime.date.today()
#        days = range(7)
#        created_list = []
#        for day in days:
#            val = today - datetime.timedelta(days=hour)
#            gats, created = GlobalAnalyticsDaySlice.get_or_create(start=val, 
#                    put=False) 
#            if created:
#                created_list.append(gats)
#        db.put(created_list)

###
# These classes initiate the map reduce jobs
###
#class EnsureHourlyAppSlices(webapp.RequestHandler):
#    """Ensures the objects for the APP STATS
#    Run as a map reduce job because we have to create an HOUR time slice
#    FOR EACH APP"""
#    def get(self):
#        mapreduce_id = control.start_map(
#            'Create Hourly Analytics Models',
#            'apps.analytics_backend.processes.ensure_hourly_slices',
#            'mapreduce.input_readers.DatastoreInputReader',
#            {'entity_kind': 'apps.app.models.App'},
#            shard_count=10
#        )
#        self.response.out.write('started: %s' % mapreduce_id)

 

################

#class EnsureDailyAppSlices(webapp.RequestHandler):
#    """Ensures the objects for the APP STATS
#    Run as a map reduce job because we have to create a DAY time slice
#    FOR EACH APP"""
#    def get(self):
#        mapreduce_id = control.start_map(
#            'Create Daily Analytics Models',
#            'apps.analytics_backend.processes.ensure_daily_slices',
#            'mapreduce.input_readers.DatastoreInputReader',
#            {'entity_kind': 'apps.app.models.App'},
#            shard_count=10
#        )
#        self.response.out.write('started: %s' % mapreduce_id)



################

#class RunHourlyActionAnalytics(webapp.RequestHandler):
#    """Runs the hour stats for all APPS"""
#    def get(self):
#        mapreduce_id = control.start_map(
#            'Computing Hourly Action Analytics',
#            'apps.analytics_backend.processes.build_hourly_stats',
#            'mapreduce.input_readers.DatastoreInputReader',
#            {'entity_kind': 'apps.analytics_backend.models.AppAnalyticsHourSlice'},
#            shard_count=10
#        )
#        self.response.out.write('started: %s' % mapreduce_id)



################

#class RunDailyActionAnalytics(webapp.RequestHandler):
#    """Runs the hour stats for all APPS"""
#    def get(self):
#        mapreduce_id = control.start_map(
#            'Computing Daily Action Analytics',
#            'apps.analytics_backend.processes.build_daily_stats',
#            'mapreduce.input_readers.DatastoreInputReader',
#            {'entity_kind': 'apps.analytics_backend.models.AppAnalyticsDaySlice'},
#            shard_count=10
#        )
#        self.response.out.write('started: %s' % mapreduce_id)




################

#class RunHourlyGlobalActionAnalytics(webapp.RequestHandler):
#    def get(self):
#        mapreduce_id = control.start_map(
#            'Computing Hourly Global Action Analytics',
#            'apps.analytics_backend.processes.build_global_hourly_stats',
#            'mapreduce.input_readers.DatastoreInputReader',
#            {'entity_kind': 'apps.analytics_backend.models.GlobalAnalyticsHourSlice'},
#            shard_count=10
#        )
#        self.response.out.write('started: %s' % mapreduce_id)


################

#class RunDailyGlobalActionAnalytics(webapp.RequestHandler):
#    def get(self):
#        mapreduce_id = control.start_map(
#            'Computing Daily Global Action Analytics',
#            'apps.analytics_backend.processes.build_global_daily_stats',
#            'mapreduce.input_readers.DatastoreInputReader',
#            {'entity_kind': 'apps.analytics_backend.models.GlobalAnalyticsDailySlice'},
#            shard_count=10
#        )
#        self.response.out.write('started: %s' % mapreduce_id)



