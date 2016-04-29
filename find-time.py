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


def get_current_user(self):
    try:
        user_key = self.auth.get_user_by_session(save_session=True)
        return DatabaseStructures.MUser.get_by_id(user_key['user_id'])
    except AttributeError:
        return None


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
<<<<<<< HEAD
            date = event.day
            day_index = date.today().weekday()
            day = DAYSOFTHEWEEK[day_index]
=======
            day = event.day
>>>>>>> 4c899a8d394b465d56172192c6d413449b80e846
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


class EventCreator(SessionsUsers.BaseHandler):
    def get(self):
        template = JINJA_ENVIRONMENT.get_template('EventCreator.html')
        self.response.write(template.render())

    def post(self):
        user = get_current_user(self)
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


class EventHandler(SessionsUsers.BaseHandler):
    def get(self):
        pass

    def create(self):
        current_user = get_current_user(self)
        title = self.request.get('title')
        location = self.request.get('location')
        description = self.request.get('description')
        invitees = self.request.getlist('invitees')
        day = self.request.get('day')

        if not current_user.user_nonrecurring_calendar:
            current_user.user_nonrecurring_calendar = DatabaseStructures.TemporaryCalendar()

        event = DatabaseStructures.Event()
        event.event_name = title
        event.event_location = location
        event.event_description = description
        event.day = day

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

        event_key = event.put()

        for inv in invitees:
            invitee = DatabaseStructures.Invitee(username=inv,
                                                 pending=True,
                                                 accepted=False,
                                                 timestamp=datetime.datetime.now(),
                                                 )
            event.attendees.append(invitee)
            u = DatabaseStructures.MUser.get_by_id(inv)
            u.user_nonrecurring_calendar.events.append(event_key)
            u.put()

        event.put()

    def post(self):
        event_key = self.request.get('event_key')
        event = event_key.get()
        event.location = self.request.get('location')
        new_invitees = self.request.get('invitees')

        for inv in new_invitees:
            invitee = DatabaseStructures.Invitee(username=inv,
                                                 pending=True,
                                                 accepted=False,
                                                 timestamp=datetime.datetime.now(),
                                                 )
            event.attendees.append(invitee)
            u = DatabaseStructures.MUSer.get_by_id(inv)
            u.user_nonrecurring_calendar.events.append(event_key)
            u.put()
        event.updated = True
        event.put()


class UserHandler(SessionsUsers.BaseHandler):
    def get(self):
        pass

    def post(self):
        pass
        


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
    webapp2.Route(r'/create_event', handler=EventCreator, name="create-event"),
    webapp2.Route(r'/login/', handler=SessionsUsers.LoginHandler, name='login'),
    webapp2.Route(r'/logout/', handler=SessionsUsers.LogoutHandler, name='logout'),
    webapp2.Route(r'/secure/', handler=SessionsUsers.SecureRequestHandler, name='secure'),
    webapp2.Route(r'/create/', handler=SessionsUsers.CreateUserHandler, name='create-user'),
    webapp2.Route(r'/event/', handler=EventHandler, name='event'),
    webapp2.Route(r'/user/', handler=UserHandler, name='user'),
], debug=True, config=webapp2_config)
