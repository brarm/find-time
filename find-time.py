import os
import urllib

from google.appengine.api import users
from google.appengine.ext import ndb

from webapp2_extras.appengine.auth import models
import jinja2
import webapp2
import datetime
import DatabaseStructures
import random
import logging
import time

import SessionsUsers

DEFAULT_GUESTBOOK_NAME = 'Default Guestbook'

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

# We set a parent key on the 'Greetings' to ensure that they are all
# in the same entity group. Queries across the single entity group
# will be consistent.  However, the write rate should be limited to
# ~1/second.


def guestbook_key(guestbook_name=DEFAULT_GUESTBOOK_NAME):
    """Constructs a Datastore key for a Guestbook entity.

    We use guestbook_name as the key.
    """
    return ndb.Key('Guestbook', guestbook_name)


class Author(ndb.Model):
    """Sub model for representing an author."""
    identity = ndb.StringProperty(indexed=False)
    email = ndb.StringProperty(indexed=False)


class Greeting(ndb.Model):
    """A main model for representing an individual Guestbook entry."""
    author = ndb.StructuredProperty(Author)
    content = ndb.StringProperty(indexed=False)
    date = ndb.DateTimeProperty(auto_now_add=True)


class MainPage(SessionsUsers.BaseHandler):
    def get(self):
        guestbook_name = self.request.get('guestbook_name',
                                          DEFAULT_GUESTBOOK_NAME)

        # Ancestor Queries, as shown here, are strongly consistent
        # with the High Replication Datastore. Queries that span
        # entity groups are eventually consistent. If we omitted the
        # ancestor from this query there would be a slight chance that
        # Greeting that had just been written would not show up in a
        # query.
        greetings_query = Greeting.query(
            ancestor=guestbook_key(guestbook_name)).order(-Greeting.date)
        greetings = greetings_query.fetch(10)

        user = users.get_current_user()
        if user:
            url = users.create_logout_url(self.request.uri)
            url_linktext = 'Logout'
        else:
            url = users.create_login_url(self.request.uri)
            url_linktext = 'Login'

        hopefully_user = self.auth.get_user_by_session(save_session=True)
        if hopefully_user:
            id = hopefully_user.keys()
            id = models.User.get_by_id(hopefully_user['user_id'])
        else:
            id = "b"
        template_values = {
            'user': user,
            'greetings': greetings,
            'guestbook_name': urllib.quote_plus(guestbook_name),
            'url': url,
            'url_linktext': url_linktext,
            # 'current_user': self.auth.get_user_by_token(user_id=id, save_session=True).keys()
            'current_user': id.unique_user_name
        }

        template = JINJA_ENVIRONMENT.get_template('index.html')
        self.response.write(template.render(template_values))


class Guestbook(webapp2.RequestHandler):
    def post(self):
        # We set the same parent key on the 'Greeting' to ensure each
        # Greeting is in the same entity group. Queries across the
        # single entity group will be consistent. However, the write
        # rate to a single entity group should be limited to
        # ~1/second.
        guestbook_name = self.request.get('guestbook_name',
                                          DEFAULT_GUESTBOOK_NAME)
        greeting = Greeting(parent=guestbook_key(guestbook_name))

        if users.get_current_user():
            greeting.author = Author(
                    identity=users.get_current_user().user_id(),
                    email=users.get_current_user().email())

        greeting.content = self.request.get('content')
        greeting.put()

        query_params = {'guestbook_name': guestbook_name}
        self.redirect('/?' + urllib.urlencode(query_params))


DAYSOFTHEWEEK = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']


class Calendar:
    """The Calendar class is generated dynamically based on events in the datastore. This object will
    provide functionality to make the javascript display simpler
    """
    daily_events = {}

    def __init__(self, user):
        for day in DAYSOFTHEWEEK:
            self.daily_events[day] = []
        logging.warning("loga")
        if user.user_recurring_calendar is None:
            logging.warning("logb")
            user.user_recurring_calendar = DatabaseStructures.WeeklyRecurringSchedule()
        logging.warning("logc")
        recurring = user.user_recurring_calendar

        self.daily_events['monday'].append(recurring.monday)
        self.daily_events['tuesday'].append(recurring.tuesday)
        self.daily_events['wednesday'].append(recurring.wednesday)
        self.daily_events['thursday'].append(recurring.thursday)
        self.daily_events['friday'].append(recurring.friday)
        self.daily_events['saturday'].append(recurring.saturday)
        self.daily_events['sunday'].append(recurring.sunday)
        logging.warning("logd")
        nonrecurring = user.user_nonrecurring_calendar
        for event in nonrecurring.events:
            day = event.beginning_day
            self.daily_events[day].append(event)

    # more functionality to be added to this class based on javascript requirements


class ProfilePage(SessionsUsers.BaseHandler):
    def get(self):
        user = self.request.get("user_name")
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
                           "user_name": user,
                           }
        template = JINJA_ENVIRONMENT.get_template('Profile.html')
        self.response.write(template.render(template_values))


class CreateUser(SessionsUsers.BaseHandler):
    def post(self):
        # allows developer to create user from main page
        display_name = self.request.get('display_name')
        user_name = self.request.get('user_name')
        email_address = self.request.get('email')

        user = DatabaseStructures.MUser()
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
        time.sleep(5)

        query_params = {'user_name': user.unique_user_name}
        self.redirect('/profile?' + urllib.urlencode(query_params))


class EventPage(SessionsUsers.BaseHandler):
    def get(self):
        template = JINJA_ENVIRONMENT.get_template('EventCreator.html')
        self.response.write(template.render())


class EventCreator(SessionsUsers.BaseHandler):
    def post(self):
        event = DatabaseStructures.Event()
        event.event_name = self.request.get("title")
        event.event_location = self.request.get("location")
        event.event_description = self.request.get("description")
        event.put()

        guestbook_name = self.request.get('guestbook_name',
                                          DEFAULT_GUESTBOOK_NAME)
        query_params = {'guestbook_name': guestbook_name}
        self.redirect('/?' + urllib.urlencode(query_params))


class LoginPage(webapp2.RequestHandler):
    def get(self):
        template = JINJA_ENVIRONMENT.get_template('SignupLogin.html')
        self.response.write(template.render())


class Login(SessionsUsers.BaseHandler):
    def get(self):
        user = DatabaseStructures.MUser()
        user.unique_user_name = self.request.get("entered_username")
        user.put()

        guestbook_name = self.request.get('guestbook_name',
                                          DEFAULT_GUESTBOOK_NAME)
        query_params = {'guestbook_name': guestbook_name}
        self.redirect('/?' + urllib.urlencode(query_params))


class Signup(SessionsUsers.BaseHandler):
    def get(self):
        user = DatabaseStructures.MUser()
        user.unique_user_name = self.request.get("entered_username")
        user.put()

        guestbook_name = self.request.get('guestbook_name',
                                          DEFAULT_GUESTBOOK_NAME)
        query_params = {'guestbook_name': guestbook_name}
        self.redirect('/?' + urllib.urlencode(query_params))

webapp2_config = {}
webapp2_config['webapp2_extras.sessions'] = {
    'secret_key': 'secret_key_123',
}

app = webapp2.WSGIApplication([
    webapp2.Route(r'/', handler=MainPage, name="main"),
    webapp2.Route(r'/profile', handler=ProfilePage, name="profile"),
    webapp2.Route(r'/create_user', handler=CreateUser),
    webapp2.Route(r'/sign', handler=Guestbook),
    webapp2.Route(r'/event_page', handler=EventPage),
    webapp2.Route(r'/create_event', handler=EventCreator, name="create-event"),
    webapp2.Route(r'/login_page', handler=LoginPage),
    webapp2.Route(r'/login', handler=Login),
    webapp2.Route(r'/signup', handler=Signup),
    # ('/login', SessionsUsers.LoginHandler),
    # ('/logout', SessionsUsers.LogoutHandler),
    # ('/secure', SessionsUsers.SecureRequestHandler),
    # ('/create', SessionsUsers.CreateUserHandler),
    webapp2.Route(r'/login/', handler=SessionsUsers.LoginHandler, name='login'),
    webapp2.Route(r'/logout/', handler=SessionsUsers.LogoutHandler, name='logout'),
    webapp2.Route(r'/secure/', handler=SessionsUsers.SecureRequestHandler, name='secure'),
    webapp2.Route(r'/create/', handler=SessionsUsers.CreateUserHandler, name='create-user'),
], debug=True, config=webapp2_config)

