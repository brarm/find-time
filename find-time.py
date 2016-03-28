import os
import urllib

from google.appengine.api import users
from google.appengine.ext import ndb

import jinja2
import webapp2
import datetime
import DatabaseStructures
import random
import logging


JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

class MainPage(webapp2.RequestHandler):
    def get(self):


        user = users.get_current_user()
        if user:
            url = users.create_logout_url(self.request.uri)
            url_linktext = 'Logout'
        else:
            url = users.create_login_url(self.request.uri)
            url_linktext = 'Login'

        template_values = {
            'user': user,
            'url': url,
            'url_linktext': url_linktext,
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
        logging.warning("user is" + user + " and has type: " + str(type(user)))

        if user.user_recurring_calendar is None:
            user.user_recurring_calendar = DatabaseStructures.WeeklyRecurringSchedule()

        recurring = user.user_recurring_calendar

        self.daily_events['monday'].append(recurring.monday.ordered())
        self.daily_events['tuesday'].append(recurring.tuesday.ordered())
        self.daily_events['wednesday'].append(recurring.wednesday.ordered())
        self.daily_events['thursday'].append(recurring.thursday.ordered())
        self.daily_events['friday'].append(recurring.friday.ordered())
        self.daily_events['saturday'].append(recurring.saturday.ordered())
        self.daily_events['sunday'].append(recurring.sunday.ordered())

        nonrecurring = user.user_nonrecurring_calendar
        for event in nonrecurring.events:
            day = DAYSOFTHEWEEK[event.beginning_day.weekday()]
            self.daily_events[day].append(event)

    # more functionality to be added to this class based on javascript requirements


class ProfilePage(webapp2.RequestHandler):
    def get(self):
        user = self.request.get("user_name")
        one_week_cal = None
        if isinstance(user, str):
            try:
                u = DatabaseStructures.User.query(DatabaseStructures.User.unique_user_name == user).fetch(1)
                one_week_cal = Calendar(u)
            except Exception:
                logging.error("User not found in the database: " + user)
                one_week_cal = None
        elif isinstance(user, DatabaseStructures.User):
            one_week_cal = Calendar(user)

        template_values = {"calendar": one_week_cal,
                           "user_name": user,
                           }
        template = JINJA_ENVIRONMENT.get_template('Profile.html')
        self.response.write(template.render(template_values))


class CreateUser(webapp2.RequestHandler):
    def post(self):
        # allows developer to create user from main page
        display_name = self.request.get('display_name')
        user_name = self.request.get('user_name')
        email_address = self.request.get('email')

        user = DatabaseStructures.User()
        user.display_name = display_name
        user.unique_user_name = user_name
        user.email_address = email_address

        # manually create calendars with events to test
        rec_events = []
        for day in DAYSOFTHEWEEK:
            for j in range(1, random.randint(1,3)):
                ev = DatabaseStructures.Event(beginning_day=day,
                                              ending_day=day,
                                              beginning_time=datetime.datetime.now().time(),
                                              ending_time=datetime.datetime.now().time().replace(hour=10),
                                              event_name=day + '_test' + str(j),
                                              event_location='this is a place',
                                              event_description='description',
                                              is_free_time=False)
                rec_events.append(ev)
        nonrec_events = []
        for i in range(1,10):
            for j in range(1, random.randint(1,3)):
                ev = DatabaseStructures.Event(beginning_day=DAYSOFTHEWEEK[i%6],
                                              ending_day=DAYSOFTHEWEEK[i%6],
                                              beginning_time=datetime.datetime.now().time(),
                                              ending_time=datetime.datetime.now().time().replace(hour=10),
                                              event_name=DAYSOFTHEWEEK[i%6] + '_test' + str(j),
                                              event_location='this is a place',
                                              event_description='description',
                                              is_free_time=False)
                nonrec_events.append(ev)
        recurring = DatabaseStructures.WeeklyRecurringSchedule()
        nonrecurring = DatabaseStructures.TemporaryCalendar()
        # recurring = DatabaseStructures.WeeklyRecurringSchedule(parent=user.key)
        # nonrecurring = DatabaseStructures.TemporaryCalendar(parent=user.key)

        rec_day_pairings = {'monday': recurring.monday,
                            'tuesday': recurring.tuesday,
                            'wednesday': recurring.wednesday,
                            'thursday': recurring.thursday,
                            'friday': recurring.friday,
                            'saturday': recurring.saturday,
                            'sunday': recurring.sunday,
                            }

        for ev in rec_events:
            rec_day_pairings[ev.beginning_day].append(ev)
        for ev in nonrec_events:
            nonrecurring.events.append(ev)
        # recurring.put()
        # nonrecurring.put()
        user.user_recurring_calendar = recurring
        user.user_nonrecurring_calendar = nonrecurring

        user.put()

        query_params = {'user_name': user.unique_user_name}
        self.redirect('/profile?' + urllib.urlencode(query_params))


class EventPage(webapp2.RequestHandler):
    def get(self):
        template = JINJA_ENVIRONMENT.get_template('EventCreator.html')
        self.response.write(template.render())


class EventCreator(webapp2.RequestHandler):
    def post(self):
        event = DatabaseStructures.Event()
        event.event_name = self.request.get("title")
        event.event_location = self.request.get("location")
        event.event_description = self.request.get("description")
        event.put()

        self.redirect('/?')


class LoginPage(webapp2.RequestHandler):
    def get(self):
        template = JINJA_ENVIRONMENT.get_template('SignupLogin.html')
        self.response.write(template.render())


class Login(webapp2.RequestHandler):
    def get(self):
        user = DatabaseStructures.User()
        user.unique_user_name = self.request.get("entered_username")
        user.put()

        self.redirect('/?')


class Signup(webapp2.RequestHandler):
    def get(self):
        user = DatabaseStructures.User()
        user.unique_user_name = self.request.get("entered_username")
        user.put()

        self.redirect('/?')

app = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/profile', ProfilePage),
    ('/create_user', CreateUser),
    ('/event_page', EventPage),
    ('/create_event', EventCreator),
    ('/login_page', LoginPage),
    ('/login', Login),
    ('/signup', Signup),
], debug=True)