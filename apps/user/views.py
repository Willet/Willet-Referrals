#!/usr/bin/env python

from apps.app.models import *
from apps.user.models import *

from util.urihandler import URIHandler

class ShowProfilePage(URIHandler):
    def get(self, app_id = None, user_id = None):
        app = get_app_by_id(app_id)
        user = get_user_by_uuid(user_id)

        if not app:
            logging.error("""Tried to get user profile without defining
                an app""")
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
                            order = OrderShopify.all().filter('order_id =', cons.order)
                            total_profit += order.subtotal_price
                    #cons = Conversion.all().filter('link =', l)
                    total_conversions += cons.count()
            if hasattr(user, 'user_testimonials'):
                testies = user.user_testimonials.filter('app =', app)
            else:
                testies = {}

            template_values = {
                'valid_user': True,
                'user': user,
                'uuid': user.uuid,
                'user_handle': user.get_handle(),
                'user_name': user.get_full_name(),
                'user_pics': user.get_pics(),
                'has_facebook': (user.get_attr('fb_name') != None),
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
        self.response.out.write(
            self.render_page(
                'profile.html', 
                template_values
            )
        )

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
                'has_facebook': (user.get_attr('fb_name') != None),
                'has_email': (user.get_attr('email') != ''),
                'reach': user.get_reach(),
                'created': str(user.get_attr('creation_time').date())
            }
            response['user'] = d
            success = True
        response['success'] = success
        self.response.out.write(json.dumps(response))


class UserCookieSafariHack( URIHandler ):
    def post( self ):
        self.get()

    def get( self ):
        user = User.get( self.request.get( 'user_uuid' ) )   
        if user:
            set_user_cookie( self, user.uuid )
        self.response.headers.add_header('P3P', P3P_HEADER)
