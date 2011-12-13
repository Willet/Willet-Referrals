#!/usr/env/python

import logging
import datetime

from google.appengine.api import memcache
from mapreduce import operation as op
from mapreduce import control
from google.appengine.ext import webapp
from google.appengine.ext import db

from django.utils import simplejson as json

from apps.analytics_backend.models import AppAnalyticsHourSlice
from apps.analytics_backend.models import AppAnalyticsDaySlice
from apps.analytics_backend.models import GlobalAnalyticsHourSlice
from apps.analytics_backend.models import GlobalAnalyticsDaySlice
from apps.analytics_backend.models import actions_to_count
from apps.action.models import Action
from apps.app.models import *
from apps.app.shopify.models import *
from apps.sibt.shopify.models import *
from apps.buttons.shopify.models import *
from apps.email.models import Email

"""
Analytics Backend!

We use the following multi step structure for generating our analytics:
    1. We create an "hour" time slice for EVERY hour for EVERY app
        This is called our "ENSURE" step.
        You'll notice that ensure_hourly_slices iterates over the App model.
        We run ENSURE for every hour/app, and for every hour "globally".
        The global hour is the sum of the individual app hours.
    2. We create a "day" time slice for every day for every app
        This is the second "ENSURE" step
        We run ensure for every day/app and for every day "globally"
    3. Now we are ready to do the real "counting". This is called the "RUN"
        step, but the methods are titled build_TIMESLICE_SCOPE where
        TIMESLICE is either hourly or daily, and SCOPE is either app or global.
        We run stats for the APP first hour/day, and then global.
        The global stats use the app hour stats and then build upon themselves
        from there.
Notes:
    - if, in the future, traffic grows significantly, the easiest way to make
        this analytics structure scale is to add smaller time slices as the
        basic unit. For example, instead of counting all actions for an hour
        slice, we instead count for every 10 minute slice.
    - we can easily add weekly/monthly/yearly stats as required
"""

def ensure_hourly_slices(app):
    """ENSURE we have the HOURLY APP time slices"""
    now = memcache.get('hour')
    if not now: 
        now = datetime.datetime.now() 
        now = now - datetime.timedelta(
                minutes=now.minute, 
                seconds=now.second, 
                microseconds=now.microsecond)
    else:
        now = datetime.datetime.combine(now, datetime.time())
    logging.debug('using now %s' % now)

    hours = range(24)
    put_list = []
    for hour in hours:
        val = now - datetime.timedelta(hours=hour)
        ahs, created = AppAnalyticsHourSlice.get_or_create(app_=app, start=val, 
                put=True)
        # Commented out the yield put because we were having issues with
        # the combined put being too large
        #if created:
        #    logging.debug('created hour slice: %s' % ahs)
        #yield op.db.Put(ahs)     

def build_hourly_stats(time_slice):
    """RUN the HOURLY APP Stats
    This is the real 'meat' that performs a count() for all actions of a 
    specific class within this time_slice"""
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
    """This is a helper method for build_hourly_stats
    Returns an Integer count for this action in the time period
    Note that with limit=None in the count() this operation will try to count
    all actions, but if it fails, it will time out."""
    return Action.all()\
        .filter('app_ =', app_)\
        .filter('class =', action)\
        .filter('created >=', start)\
        .filter('created <=', end)\
        .filter('is_admin =', False)\
        .count(limit=None)

def ensure_daily_slices(app):
    """ENSURE the DAILY APP slices are present"""
    today = memcache.get('day')
    if not today:
        today = datetime.date.today()
    today = datetime.datetime.combine(today, datetime.time())

    days = range(7)
    put_list = []
    for day in days:
        val = today - datetime.timedelta(days=day)
        ahs, created = AppAnalyticsDaySlice.get_or_create(app_=app, start=val, 
                put=True)
        # Again, commented out the yield put for now due to errors putting
        #if created:
        #    logging.debug('created day slice: %s' % ahs)
        #yield op.db.Put(ahs)      

def build_daily_stats(time_slice):
    """BUILD the DAILY APP specific stats"""
    start = time_slice.start
    end = time_slice.end
    app_ = time_slice.app_

    # app engine is a fucking whore.
    hour_slices = AppAnalyticsHourSlice.all()\
            .filter('app_ =', app_)\
            .filter('start >=', start)\
            .filter('start <', end)

    action_first_run = []
    logging.debug('getting day stats for day: %s\nslices: %d' % (
        start, hour_slices.count()))

    for hour_slice in hour_slices:
        for action in actions_to_count:
            if action not in action_first_run:
                # because we want this to be idempotent, we default the stats
                # to zero each time we run
                time_slice.default(action)
                action_first_run.append(action)
            hour_value = hour_slice.get_attr(action)
            time_slice.increment(action, hour_value)

    yield op.db.Put(time_slice)

def build_global_hourly_stats(global_slice):
    """BUILD the HOURLY GLOBAL stats"""
    start = global_slice.start
    end = global_slice.end

    hour_slices = AppAnalyticsHourSlice.all()\
            .filter('start >=', start)\
            .filter('start <', end)
    action_first_run = []

    logging.info('Hour: %s\n%d slices' % (start, hour_slices.count()))

    for hour_slice in hour_slices:
        for action in actions_to_count:
            if action not in action_first_run:
                # defaults and for idempotent
                global_slice.default(action)
                action_first_run.append(action)
            logging.debug('incrementing %s from %d to %d' % (
                action, global_slice.get_attr(action), 
                hour_slice.get_attr(action)))
            global_slice.increment(action, hour_slice.get_attr(action))
    yield op.db.Put(global_slice)

def build_global_daily_stats(global_slice):
    """BUILD the DAILY GLOBAL stats"""
    start = global_slice.start
    end = global_slice.end

    hour_slices = GlobalAnalyticsHourSlice.all()\
            .filter('start >=', start)\
            .filter('start <', end)
    action_first_run = []

    for hour_slice in hour_slices:
        for action in actions_to_count:
            if action not in action_first_run:
                global_slice.default(action)
                action_first_run.append(action)
            global_slice.increment(action, hour_slice.get_attr(action))
    yield op.db.Put(global_slice)

class TimeSlices(webapp.RequestHandler):
    def get(self, action, scope):
        """Handler to run our analytics methods. Because there is a lot of
        duplicated code, we use this convoluted options dict.
        We break the dict up by actions and scope.
        Actions are: ensure, run (synonymous with build)
        Scopes are: hour, day, hour_global, day_global
        
        Some of the ENSURE jobs are mapreduce jobs, while the global jobs
        are just simple db.puts.

        Someone may hate how this is setup in the future, but I felt having
        one handler method was better than having 8 very similar methods with
        duplicated code all over the place. This has allowed me to make rapid
        changes as I've been designing the analytics backend."""

        e_base = 'apps.analytics_backend.models.%s'
        f_base = 'apps.analytics_backend.processes.%s'
        options = {
            'ensure': {
                'hour':{
                    'mr': {
                        'name': 'Create Hourly Analytics Models',
                        'func': f_base % 'ensure_hourly_slices',
                        'entity': 'apps.app.models.App',
                        'reader': 'DatastoreKeyInputReader'
                    } 
                },
                'day': {
                    'mr': {
                        'name': 'Create Daily Analytics Models',
                        'func': f_base % 'ensure_daily_slices',
                        'entity': 'apps.app.models.App',
                        'reader': 'DatastoreKeyInputReader'
                    }
                },
                'hour_global': {
                    'scope_range': range(24),
                    'today_get': datetime.datetime.today(),
                    'today': lambda d: d - datetime.timedelta(
                        minutes=d.minute, 
                        seconds=d.second, 
                        microseconds=d.microsecond),
                    'td': lambda t: datetime.timedelta(hours=t),
                    'cls': GlobalAnalyticsHourSlice,
                },
                'day_global': {
                    'scope_range': range(7),
                    'today_get': datetime.date.today(),
                    'today': lambda d: datetime.datetime.combine(d, datetime.time()),
                    'td': lambda t: datetime.timedelta(days=t),
                    'cls': GlobalAnalyticsDaySlice,
                }
            }, 
            'run': {
                'hour': {
                    'name': 'Run Hourly Analytics',
                    'func': f_base % 'build_hourly_stats',
                    'entity': e_base % 'AppAnalyticsHourSlice',
                    'done_callback': '/bea/run/day/', 
                },
                'day': {
                    'name': 'Run Daily Analytics',
                    'func': f_base % 'build_daily_stats',
                    'entity': e_base % 'AppAnalyticsDaySlice',
                    'done_callback': '/bea/run/hour_global/', 
                },
                'hour_global': {
                    'name': 'Run GLOBAL Hourly Analytics',
                    'func': f_base % 'build_global_hourly_stats',
                    'entity': e_base % 'GlobalAnalyticsHourSlice',
                    'done_callback': '/bea/run/day_global/', 
                },
                'day_global': {
                    'name': 'Run GLOBAL Daily Analytics',
                    'func': f_base % 'build_global_daily_stats',
                    'entity': e_base % 'GlobalAnalyticsDaySlice',
                    'done_callback': '/bea/done/', 
                },
            }
        }
        oas = options[action][scope]
        if action == 'ensure':
            if 'mr' not in oas:
                today = oas['today']
                scope_range = oas['scope_range']
                created_list = []
                base_date = memcache.get(scope)
                if not base_date:
                    base_date = oas['today_get']
                base_date = oas['today'](base_date)
                for period in scope_range:
                    val = base_date - oas['td'](period)
                    entity, created = oas['cls'].get_or_create(start=val, put=False)
                    if created:
                        created_list.append(entity)
                db.put(created_list)
                data = {'success': True, 'mesage': 'Put: %s' % len(created_list)}
                self.response.out.write(json.dumps(data))
                return
            else:
                mr = oas['mr']
        else:
            mr = options[action][scope]
        if 'reader' in mr:
            reader = 'mapreduce.input_readers.%s' % mr['reader']
        else:
            reader = 'mapreduce.input_readers.DatastoreInputReader'
        mapreduce_parameters = {}
        if 'done_callback' in mr:
            mapreduce_parameters['done_callback'] = mr['done_callback']
        mapreduce_id = control.start_map(
            mr['name'],
            mr['func'],
            reader, {
                'entity_kind': mr['entity'],
                'batch_size': 25
            },
            mapreduce_parameters = mapreduce_parameters,
            shard_count=20
        )
        data = {'success': True, 'mapreduce_id': mapreduce_id}
        self.response.out.write(json.dumps(data))

class AnalyticsDone(webapp.RequestHandler):
    def get(self):
        Email.emailBarbara('Finished running analytics')
        self.response.out.write(json.dumps({'success': True}))


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



