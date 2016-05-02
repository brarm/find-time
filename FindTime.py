import os
import urllib

from google.appengine.ext import ndb

import jinja2
import webapp2
import datetime
import DatabaseStructures
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
        user_id = None
        if hopefully_user:
            user_id = get_current_user(self).unique_user_name
        template_values = {
            'current_user': user_id,
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
            day = event.day
            # day_index = date.today().weekday()
            # day = DAYSOFTHEWEEK[day_index]
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

class AddFriend(SessionsUsers.BaseHandler):
    def post(self):
        user_key = self.auth.get_user_by_session(save_session=True)
        user = DatabaseStructures.MUser.get_by_id(user_key['user_id'])
        user2 = self.request.get('user')
        if isinstance(user2, unicode):
            user2 = str(user2)
        friend1 = ndb.StructuredProperty(DatabaseStructures.Friend, indexed=False)
        friend1.status = False
        friend1.pending = True
        friend1.username = user.unique_user_name
        friend1.timestamp = datetime.time
        friend2 = ndb.StructuredProperty(DatabaseStructures.Friend, indexed=False)
        friend2.status = False
        friend2.pending = False
        friend2.username = user2
        friend2.timestamp = datetime.time
        try:
            u2 = DatabaseStructures.MUser.query(DatabaseStructures.MUser.unique_user_name == user2).fetch(1)
            user_obj = u2[0]
            user.friends.add(friend2)
            u2.friends.add(friend1)
        except Exception as e:
            logging.error(str(type(e)))
            logging.error(str(e))
            logging.error("User not found in the database: " + user)
        self.redirect('/profile?')

class AcceptFriend:
    def post(self):
        user_key = self.auth.get_user_by_session(save_session=True)
        user = DatabaseStructures.MUser.get_by_id(user_key['user_id'])
        user2 = self.request.get('user')
        if isinstance(user2, unicode):
            user2 = str(user2)
        try:
            u2 = DatabaseStructures.MUser.query(DatabaseStructures.MUser.unique_user_name == user2).fetch(1)
            user_obj = u2[0]
            for friend in user.friends:
                if(friend.username == user2):
                    friend.status =True
                    friend.pending = False
            for friend in u2.friends:
                if (friend.username == user.unique_user_name):
                    friend.status = True
                    friend.pending = False

        except Exception as e:
            logging.error(str(type(e)))
            logging.error(str(e))
            logging.error("User not found in the database: " + user)
        self.redirect('/profile?')

class RemoveFriend:
    def post(self):
        user_key = self.auth.get_user_by_session(save_session=True)
        user = DatabaseStructures.MUser.get_by_id(user_key['user_id'])
        user2 = self.request.get('user')
        if isinstance(user2, unicode):
            user2 = str(user2)
        try:
            u2 = DatabaseStructures.MUser.query(DatabaseStructures.MUser.unique_user_name == user2).fetch(1)
            user_obj = u2[0]
            for friend in user.friends:
                if (friend.username == user2):
                    user.friends.remove(friend)
            for friend in u2.friends:
                if (friend.username == user.unique_user_name):
                   u2.friends.remove(friend)

        except Exception as e:
            logging.error(str(type(e)))
            logging.error(str(e))
            logging.error("User not found in the database: " + user)
        self.redirect('/profile?')

class Search:
    def search(self):
        search = self.request.get('search')
        u = DatabaseStructures.MUser.query(search == DatabaseStructures.MUser.unique_user_name or search == DatabaseStructures.MUser.display_name).fetch(1)
        if(u != None):
            return u
        u = DatabaseStructures.MUser.query(search in DatabaseStructures.MUser.unique_user_name or search in DatabaseStructures.MUser.display_name).fetch(all)
        return u

class RecurringEvents(SessionsUsers.BaseHandler):
    def get(self):
        pass

    def post(self):
        # blocks will have id in form
        pass

class EventModifier(SessionsUsers.BaseHandler):
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

class EventHandler(SessionsUsers.BaseHandler):
    def get(self):
        
        template = JINJA_ENVIRONMENT.get_template('EventCreator.html')
        self.response.write(template.render())

    def post(self):
        current_user = get_current_user(self)
        title = self.request.get('title')
        location = self.request.get('location')
        description = self.request.get('description')
        invitees = self.request.get('invitees', allow_multiple=True)
        logging.error("INVITEES IS OF TYPE : " + str(type(invitees)))
        day = self.request.get('day')

        today_index = datetime.datetime.today().weekday()
        day_index = DAYSOFTHEWEEK.index(day)
        diff = day_index - today_index
        date = datetime.datetime.today() + datetime.timedelta(days=diff)

        if not current_user.user_nonrecurring_calendar:
            current_user.user_nonrecurring_calendar = DatabaseStructures.TemporaryCalendar()

        event = DatabaseStructures.Event()
        event.event_name = title
        event.event_location = location
        event.event_description = description
        event.day = date

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


class UserHandler(SessionsUsers.BaseHandler):
    def get(self):
        pass

    def post(self):
        pass

    def recurring(self):


        
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
    webapp2.Route(r'/event/create', handler=EventHandler, name="create-event"),
    webapp2.Route(r'/<event>/modify', handler=EventHandler, name="event"),
    webapp2.Route(r'/login', handler=SessionsUsers.LoginHandler, name='login'),
    webapp2.Route(r'/logout', handler=SessionsUsers.LogoutHandler, name='logout'),
    webapp2.Route(r'/secure', handler=SessionsUsers.SecureRequestHandler, name='secure'),
    webapp2.Route(r'/create', handler=SessionsUsers.CreateUserHandler, name='create-user'),
    webapp2.Route(r'/event', handler=EventHandler, name='event'),
    webapp2.Route(r'/user', handler=UserHandler, name='user'),
    webapp2.Route(r'/recurring', handler=RecurringEvents, name='recurring')
], debug=True, config=webapp2_config)
