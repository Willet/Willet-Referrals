#!/usr/bin/env python

__author__ = "Willet, Inc."
__copyright__ = "Copyright 2011, Willet, Inc"

from google.appengine.api import memcache, taskqueue, urlfetch
from google.appengine.ext import webapp
import django.utils.simplejson as json

from apps.app.models import App, ShareCounter
from apps.buttons.shopify.models import ButtonsShopify
from apps.user.models import *
from util.consts import *
from util.helpers import *
from util.urihandler import URIHandler


class BatchRequest(URIHandler):
    """ I-CAN'T-BELIEVE-IT'S-EXPERIMENTAL: Start a batch request of a class
        method, which will run for every app of app_cls in the db """
    def get(self):
        self.post()

    def post(self):
        """ Expected inputs:
            - app_cls    : App class
            - method     : method to call on app_cls
            - batch_size*: 0 - 1000, 100 is good in general
            - offset    *: database offset
            - params    *: JSON-encoded parameters to send to method
            - criteria  *: JSON-encoded matching criteria
                           to filter (equality only)
                           NOTE: the criteria need to be indexed!
            - exclude_uninstalled*: 1 if we want to exclude uninstalled apps

            *Optional
        """
        app_cls        = self.request.get('app_cls')
        method         = self.request.get('method')

        batch_size     = int(self.request.get('batch_size', 100))
        offset         = int(self.request.get('offset', 0))
        params         = json.loads(self.request.get('params', "{}"))
        criteria       = json.loads(self.request.get('criteria', "{}"))

        exclude_val    = int(self.request.get('exclude_uninstalled', 0))
        exclude        = True if exclude_val == 1 else False

        filter_obj     = None

        logging.warn('Running BatchRequest for %s.%s from %i to %i' % (
            app_cls, method, offset, offset+batch_size-1))

        # Convert JSON keys from unicode to strings
        # Python 2.5 doesn't like this, but it will work in 2.7
        # We do this because we will be using the keys as kwargs
        converted_params = dict( (key.encode('utf-8'), value) for key, value in params.iteritems() )

        # Check that class is callable
        if app_cls:
            if app_cls[0] == '_':
                logging.error('app_cls is private')
                self.error(403) # Access Denied, Private class
                return
            try:
                filter_obj = globals()[app_cls].all()
            except AttributeError:
                logging.error('app_cls is not a valid model')
                self.error(400)
                return
            except KeyError:
                logging.error('app_cls is not in scope')
                self.error(400)
                return
        else:
            logging.error('app_cls missing')
            self.error(400)
            return

        # Check that method is safe and callable
        if method:
            if method[0] == '_':
                logging.error('method is private')
                self.error(403) # Access Denied, Private method
                return
            try:
                if not hasattr(getattr(globals()[app_cls], method), '__call__'):
                    raise AttributeError
            except AttributeError:
                logging.error('method is not valid')
                self.error(400) # Bad Request
                return
        else:
            logging.error('method missing')
            self.error(400)
            return

        # Get model instances
        for ukey, value in criteria.iteritems():
            key = " %s =" % ukey.encode('utf-8')
            filter_obj.filter(key, value)

        apps = filter_obj.fetch(limit=batch_size, offset=offset)

        # If reached batch size, start another batch at the next offset
        if len(apps) == batch_size:
            p = {
                'batch_size'         : batch_size,
                'offset'             : offset + batch_size,
                'app_cls'            : app_cls,
                'method'             : method,
                'params'             : json.dumps(params),
                'criteria'           : json.dumps(criteria),
                'exclude_uninstalled': exclude_val
            }
            taskqueue.add(url=url('BatchRequest'), params=p)

        # For each app, try to create an email & send it
        for app in apps:
            try:
                if exclude and hasattr(app, "client") and not getattr(app, "client"):
                    logging.info('%s.%s has no client. Probably uninstalled' %
                                 (app.__class__.__module__,
                                  app.__class__.__name__,))
                    continue

                getattr(app, method)(**converted_params)
                logging.info('%s.%s.%s() succeeded' % (app.__class__.__module__,
                                                       app.__class__.__name__,
                                                       method))
            except Exception, e:
                logging.error('%s.%s.%s() failed because %r' % (app.__class__.__module__,
                                                               app.__class__.__name__,
                                                               method,
                                                               e))
                continue


class BatchStoreSurvey(URIHandler):
    """ Gets information about every ButtonShopify store, and emails Fraser """
    def get(self):
        self.post()

    def post(self):
        """ Expected inputs:
            - batch_size*: 0 - 1000, 100 is good in general
            - offset    *: database offset
            - params    *: JSON-encoded parameters to send to method
            - criteria  *: JSON-encoded matching criteria
                           to filter (equality only)
                           NOTE: the criteria need to be indexed!
            - exclude_uninstalled*: 1 if we want to exclude uninstalled apps

            *Optional
        """
        app_cls        = 'ButtonsShopify'
        method         = 'get_monthly_orders'

        batch_size     = int(self.request.get('batch_size', 100))
        offset         = int(self.request.get('offset', 0))
        params         = json.loads(self.request.get('params', "{}"))
        criteria       = json.loads(self.request.get('criteria', "{}"))

        exclude_val    = int(self.request.get('exclude_uninstalled', 1))
        exclude        = True if exclude_val == 1 else False

        filter_obj     = None

        logging.warn('Running BatchStoreSurvey for %s.%s from %i to %i' % (app_cls,
                                                                       method,
                                                                       offset,
                                                                       offset+batch_size-1))

        # Convert JSON keys from unicode to strings
        # Python 2.5 doesn't like this, but it will work in 2.7
        # We do this because we will be using the keys as kwargs
        converted_params = dict( (key.encode('utf-8'), value) for key, value in params.iteritems() )

        # Check that class is callable
        if app_cls:
            if app_cls[0] == '_':
                logging.error('app_cls is private')
                self.error(403) # Access Denied, Private class
                return
            try:
                filter_obj = globals()[app_cls].all()
            except AttributeError:
                logging.error('app_cls is not a valid model')
                self.error(400)
                return
            except KeyError:
                logging.error('app_cls is not in scope')
                self.error(400)
                return
        else:
            logging.error('app_cls missing')
            self.error(400)
            return

        # Check that method is safe and callable
        if method:
            if method[0] == '_':
                logging.error('method is private')
                self.error(403) # Access Denied, Private method
                return
            try:
                if not hasattr(getattr(globals()[app_cls], method), '__call__'):
                    raise AttributeError
            except AttributeError:
                logging.error('method is not valid')
                self.error(400) # Bad Request
                return
        else:
            logging.error('method missing')
            self.error(400)
            return

        # Get model instances
        for ukey, value in criteria.iteritems():
            key = " %s =" % ukey.encode('utf-8')
            filter_obj.filter(key, value)

        apps = filter_obj.fetch(limit=batch_size, offset=offset)

        # If reached batch size, start another batch at the next offset
        if len(apps) == batch_size:
            p = {
                'batch_size'         : batch_size,
                'offset'             : offset + batch_size,
                'app_cls'            : app_cls,
                'method'             : method,
                'params'             : json.dumps(params),
                'criteria'           : json.dumps(criteria),
                'exclude_uninstalled': exclude_val
            }
            taskqueue.add(url=url('BatchStoreSurvey'), params=p)

        body = u'Monthly sales / store name / store url / contact name / contact url<br />'

        # For each app, try to create an email & send it
        for app in apps:
            try:
                if exclude and hasattr(app, "client") and not getattr(app, "client"):
                    logging.info('%s.%s has no client. Probably uninstalled' %
                                 (app.__class__.__module__,
                                  app.__class__.__name__,))
                    continue

                result = getattr(app, method)(**converted_params)

                body += u'%s %s %s %s &lt;%s&gt;<br />' % result

                logging.info('%s.%s.%s() succeeded' % (app.__class__.__module__,
                                                       app.__class__.__name__,
                                                       method))
            except Exception, e:
                logging.error('%s.%s.%s() failed because %r' % (app.__class__.__module__,
                                                               app.__class__.__name__,
                                                               method,
                                                               e))
                continue

        # Email DevTeam
        Email.emailDevTeam(body, subject='ShopConnection Survey')



class AppClicksCounter(URIHandler):
    def post(self):
        app = App.get(self.request.get('app_uuid'))

        app.cached_clicks_count = 0
        if hasattr(app, 'links_'):
            for l in app.links_:
                app.cached_clicks_count += l.count_clicks()

        app.put()

