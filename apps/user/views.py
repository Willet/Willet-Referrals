#!/usr/bin/env python

from apps.campaign.models import *
from apps.user.models import *

from util.urihandler import URIHandler

class ShowProfilePage(URIHandler):
    def get(self, campaign_id = None, user_id = None):
        campaign = get_campaign_by_id(campaign_id)
        user = get_user_by_uuid(user_id)

        if not campaign:
            logging.error("""Tried to get user profile without defining
                a campgin""")
        elif user:
            links = Link.all().filter('user =', user)
            total_clicks = 0
            total_conversions = 0
            total_profit = 0
            for l in links:
                total_clicks += l.count_clicks()
                if hasattr(l, 'link_conversions'):
                    cons = l.link_conversions
                    for c in cons:
                        if type(cons.order) == type(str()):
                            order = ShopifyOrder.all().filter('order_id =', cons.order)
                            total_profit += order.subtotal_price
                    #cons = Conversion.all().filter('link =', l)
                    total_conversions += cons.count()
            #user_analytics = user.get_analytics_for_campaign(campaign, 'day')
            #results = user_analytics.fetch(user_analytics.count())
            #logging.info("got %d results" % user_analytics.count())
            #logging.info(results)
            if hasattr(user, 'user_testimonials'):
                testies = user.user_testimonials.filter('campaign =', campaign)
            else:
                testies = {}

            template_values = {
                'valid_user': True,
                'user': user,
                'uuid': user.uuid,
                'user_handle': user.get_handle(),
                'user_name': user.get_full_name(),
                'user_pics': user.get_pics(),
                'user_kscore': user.get_attr('kscore'),
                'has_twitter': (user.get_attr('twitter_handle') != None),
                'has_facebook': (user.get_attr('fb_name') != None),
                'has_linkedin': (user.get_attr('linkedin_first_name') != None),
                'has_email': (user.get_attr('email') != ''),
                'reach': user.get_reach(),
                'created': str(user.get_attr('creation_time').date()),
                'total_clicks': total_clicks,
                'total_conversions': total_conversions,
                'total_referrals': links.count(),
                'total_profit': total_profit,
                'testies': testies,
                #'results': results 
            }
        else:
            template_values = {
                'uuid': user_id,
                'user': None,
                'valid_user': False
            }
        self.response.out.write(self.render_page('profile.html', template_values))

class ShowProfileJSON (URIHandler):
    def get(self, user_id = None):
        user = get_user_by_uuid(user_id)
        response = {}
        success = False
        if user:
            #response['user'] = user
            d = {
                'uuid': user.uuid,
                'handle': user.get_handle(),
                'name': user.get_full_name(),
                'pic': user.get_attr('pic'),
                'kscore': user.get_attr('kscore'),
                'has_twitter': (user.get_attr('twitter_handle') != None),
                'has_facebook': (user.get_attr('fb_name') != None),
                'has_linkedin': (user.get_attr('linkedin_first_name') != None),
                'has_email': (user.get_attr('email') != ''),
                'reach': user.get_reach(),
                'created': str(user.get_attr('creation_time').date())
            }
            response['user'] = d
            success = True
        response['success'] = success
        self.response.out.write(json.dumps(response))


