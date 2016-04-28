import os
import urllib

from google.appengine.ext import ndb

import jinja2
import webapp2
import datetime
import DatabaseStructures
import random
import logging
import time

import SessionsUsers

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)


class MainPage(SessionsUsers.BaseHandler):
    def get(self):
        hopefully_user = self.auth.get_user_by_session(save_session=True)
        if hopefully_user:
            id = DatabaseStructures.MUser.get_by_id(hopefully_user['user_id']).unique_user_name
            DatabaseStructures.MUser.get_by_id(hopefully_user['user_id']).email_address = "butts.com"
            email = DatabaseStructures.MUser.get_by_id(hopefully_user['user_id']).email_address

        else:
            id = None
            email = None
        template_values = {
            'current_user': id,
            'email': email,
            # 'calendar': cal
        }

        template = JINJA_ENVIRONMENT.get_template('index.html')
        self.response.write(template.render(template_values))


DAYSOFTHEWEEK = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']

class Calendar:
    """The Calendar class is generated dynamically based on events in the datastore. This object will
    provide functionality to make the javascript display simpler
    """
    daily_events = {}

    def __init__(self, user):
        for day in DAYSOFTHEWEEK:
            self.daily_events[day] = []
        if not user.user_recurring_calendar:
            user.user_recurring_calendar = DatabaseStructures.WeeklyRecurringSchedule()
        if not user.user_nonrecurring_calendar:
            user.user_nonrecurring_calendar = DatabaseStructures.TemporaryCalendar()

        recurring = user.user_recurring_calendar

        self.daily_events['monday'].append(recurring.monday)
        self.daily_events['tuesday'].append(recurring.tuesday)
        self.daily_events['wednesday'].append(recurring.wednesday)
        self.daily_events['thursday'].append(recurring.thursday)
        self.daily_events['friday'].append(recurring.friday)
        self.daily_events['saturday'].append(recurring.saturday)
        self.daily_events['sunday'].append(recurring.sunday)
        nonrecurring = user.user_nonrecurring_calendar
        for event_key in nonrecurring.events:
            event = event_key.get()
            day = event.beginning_day
            self.daily_events[day].append(event)
        for key in self.daily_events:
            for ev in self.daily_events[key]:
                if not ev:
                    self.daily_events[key].remove(ev)

    # more functionality to be added to this class based on javascript requirements


class ProfilePage(SessionsUsers.BaseHandler):
    def get(self):
        user_key = self.auth.get_user_by_session(save_session=True)
        user = DatabaseStructures.MUser.get_by_id(user_key['user_id'])
        one_week_cal = None
        if isinstance(user, unicode):
            user = str(user)

        if isinstance(user, str):
            try:
                u = DatabaseStructures.MUser.query(DatabaseStructures.MUser.unique_user_name == user).fetch(1)
                user_obj = u[0]
                one_week_cal = Calendar(user_obj)
            except Exception as e:
                logging.error(str(type(e)))
                logging.error(str(e))
                logging.error("User not found in the database: " + user)
                one_week_cal = None
        elif isinstance(user, DatabaseStructures.MUser):
            one_week_cal = Calendar(user)

        template_values = {"calendar": one_week_cal,
                           "user_name": user.unique_user_name,
                           }
        template = JINJA_ENVIRONMENT.get_template('Profile.html')
        self.response.write(template.render(template_values))

#
# class CreateUser(SessionsUsers.BaseHandler):
#     def post(self):
#         # allows developer to create user from main page
#         display_name = self.request.get('display_name')
#         user_name = self.request.get('user_name')
#         email_address = self.request.get('email')
#
#         user = DatabaseStructures.MUser()
#         user.display_name = display_name
#         user.unique_user_name = user_name
#         user.email_address = email_address
#
#         # manually create calendars with events to test
#         rec_events = []
#         for day in DAYSOFTHEWEEK:
#             for j in range(1, random.randint(1,3)):
#                 ev = DatabaseStructures.Event(beginning_day=day,
#                                               ending_day=day,
#                                               beginning_time=datetime.datetime.now().time(),
#                                               ending_time=datetime.datetime.now().time().replace(hour=10),
#                                               event_name=day + '_test' + str(j),
#                                               event_location='this is a place',
#                                               event_description='description',
#                                               is_free_time=False)
#                 rec_events.append(ev)
#         nonrec_events = []
#         for i in range(1,10):
#             for j in range(1, random.randint(1,3)):
#                 ev = DatabaseStructures.Event(beginning_day=DAYSOFTHEWEEK[i%6],
#                                               ending_day=DAYSOFTHEWEEK[i%6],
#                                               beginning_time=datetime.datetime.now().time(),
#                                               ending_time=datetime.datetime.now().time().replace(hour=10),
#                                               event_name=DAYSOFTHEWEEK[i%6] + '_test' + str(j),
#                                               event_location='this is a place',
#                                               event_description='description',
#                                               is_free_time=False)
#                 nonrec_events.append(ev)
#         recurring = DatabaseStructures.WeeklyRecurringSchedule()
#         nonrecurring = DatabaseStructures.TemporaryCalendar()
#         # recurring = DatabaseStructures.WeeklyRecurringSchedule(parent=user.key)
#         # nonrecurring = DatabaseStructures.TemporaryCalendar(parent=user.key)
#
#         rec_day_pairings = {'monday': recurring.monday,
#                             'tuesday': recurring.tuesday,
#                             'wednesday': recurring.wednesday,
#                             'thursday': recurring.thursday,
#                             'friday': recurring.friday,
#                             'saturday': recurring.saturday,
#                             'sunday': recurring.sunday,
#                             }
#
#         for ev in rec_events:
#             rec_day_pairings[ev.beginning_day].append(ev)
#         for ev in nonrec_events:
#             nonrecurring.events.append(ev)
#         user.user_recurring_calendar = recurring
#         user.user_nonrecurring_calendar = nonrecurring
#
#         user.put()
#         time.sleep(5)
#
#         query_params = {'user_name': user.unique_user_name}
#         self.redirect('/profile?' + urllib.urlencode(query_params))


class EventCreator(SessionsUsers.BaseHandler):
    def get(self):
        template = JINJA_ENVIRONMENT.get_template('EventCreator.html')
        self.response.write(template.render())

    def post(self):
        user_key = self.auth.get_user_by_session(save_session=True)
        user = DatabaseStructures.MUser.get_by_id(user_key['user_id'])
        if not user.user_nonrecurring_calendar:
            user.user_nonrecurring_calendar = DatabaseStructures.TemporaryCalendar()

        event = DatabaseStructures.Event()
        event.event_name = self.request.get("title")
        event.event_location = self.request.get("location")
        event.event_description = self.request.get("description")
        event.beginning_day = self.request.get("day")
        event.ending_day = self.request.get("day")

        start_ampm = self.request.get("start_time_ampm")
        hr = int(self.request.get("start_time_hr")) % 12
        start_hr = hr if start_ampm == "am" else hr + 12
        start_min = int(self.request.get("start_time_min"))
        start_time = datetime.time(start_hr, start_min)
        event.beginning_time = start_time
        end_ampm = self.request.get("end_time_ampm")
        hr = int(self.request.get("end_time_hr")) % 12
        end_hr = hr if end_ampm == "am" else hr + 12
        end_min = int(self.request.get("end_time_min"))
        end_time = datetime.time(end_hr, end_min)
        event.ending_time = end_time

        key = event.put()
        logging.error(key)
        user.user_nonrecurring_calendar.events.append(key)
        user.put()

        self.redirect('/profile?')

#
# class LoginPage(webapp2.RequestHandler):
#     def get(self):
#         template = JINJA_ENVIRONMENT.get_template('SignupLogin.html')
#         self.response.write(template.render())
#
#
# class Login(SessionsUsers.BaseHandler):
#     def get(self):
#         user = DatabaseStructures.MUser()
#         user.unique_user_name = self.request.get("entered_username")
#         user.put()
#
#         self.redirect('/?')

#
# class Signup(SessionsUsers.BaseHandler):
#     def get(self):
#         user = DatabaseStructures.MUser()
#         user.unique_user_name = self.request.get("entered_username")
#         user.put()
#
#         self.redirect('/?')

webapp2_config = {}
webapp2_config['webapp2_extras.sessions'] = {
    'secret_key': 'secret_key_123',
}
webapp2_config['webapp2_extras.auth'] = {
    'user_model': DatabaseStructures.MUser,
}
app = webapp2.WSGIApplication([
    webapp2.Route(r'/', handler=MainPage, name="main"),
    webapp2.Route(r'/profile', handler=ProfilePage, name="profile"),
    # webapp2.Route(r'/create_user', handler=CreateUser),
    # webapp2.Route(r'/event_page', handler=EventPage),
    webapp2.Route(r'/create_event', handler=EventCreator, name="create-event"),
    # webapp2.Route(r'/login_page', handler=LoginPage),
    # webapp2.Route(r'/login', handler=Login),
    # webapp2.Route(r'/signup', handler=Signup),
    # ('/login', SessionsUsers.LoginHandler),
    # ('/logout', SessionsUsers.LogoutHandler),
    # ('/secure', SessionsUsers.SecureRequestHandler),
    # ('/create', SessionsUsers.CreateUserHandler),
    webapp2.Route(r'/login/', handler=SessionsUsers.LoginHandler, name='login'),
    webapp2.Route(r'/logout/', handler=SessionsUsers.LogoutHandler, name='logout'),
    webapp2.Route(r'/secure/', handler=SessionsUsers.SecureRequestHandler, name='secure'),
    webapp2.Route(r'/create/', handler=SessionsUsers.CreateUserHandler, name='create-user'),
], debug=True, config=webapp2_config)
