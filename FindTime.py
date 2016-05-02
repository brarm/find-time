import os
from google.appengine.api import mail
from google.appengine.ext import ndb
import jinja2
import webapp2
import datetime
import DatabaseStructures
import logging

import SessionsUsers

from jinja2.ext import autoescape

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

class TestPage(SessionsUsers.BaseHandler):
    def get(self):
        hopefully_user = self.auth.get_user_by_session(save_session=True)
        user_id = None
        if hopefully_user:
            user_id = get_current_user(self).unique_user_name
        template_values = {
            'current_user': user_id,
        }

        template = JINJA_ENVIRONMENT.get_template('TestPage.html')
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
            day_index = datetime.datetime.today().weekday()
            day = DAYSOFTHEWEEK[day_index]
            self.daily_events[day].append(event)
        for key in self.daily_events:
            for ev in self.daily_events[key]:
                if not ev:
                    self.daily_events[key].remove(ev)

    # more functionality to be added to this class based on javascript requirements


class ProfilePage(SessionsUsers.BaseHandler):
    def get(self):
        current_user = get_current_user(self)
        dest_user = DatabaseStructures.MUser.get_by_id(profile_id)

        relation_state = None

        one_week_cal = Calendar(dest_user)
        friends_list = dest_user.friends
        # dest_user.friends.query(DatabaseStructures.Friend.username == current_user.unique_user_name).fetch()
        # if not empty, grab first element
        if current_user == dest_user:
            relation_state = 'same_user'


        #friends = user_obj.friends

        template_values = {"calendar": one_week_cal,
                           "user_name": current_user.unique_user_name,
                           "friends": current_user.friends
                           }
        template = JINJA_ENVIRONMENT.get_template('Profile.html')
        self.response.write(template.render(template_values))


class AddFriend(SessionsUsers.BaseHandler):
    def post(self):
        user_key = self.auth.get_user_by_session(save_session=True)
        user = DatabaseStructures.MUser.get_by_id(user_key['user_id'])
        user2 = self.request.get('user')
        friend1 = DatabaseStructures.Friend(accepted=False, pending=True, username=user.unique_user_name,
                                            timestamp=datetime.datetime.now())
        friend2 = DatabaseStructures.Friend(accepted=False, pending=False, username=user2,
                                            timestamp=datetime.datetime.now())
        try:
            u2 = DatabaseStructures.MUser.query(user2 == DatabaseStructures.MUser.unique_user_name).fetch(1)
            user_obj = u2[0]
            if user.friends is None:
                user.friends = ndb.StructuredProperty(DatabaseStructures.Friend, repeated=True)
            if user_obj.friends is None:
                user_obj.friends = ndb.StructuredProperty(DatabaseStructures.Friend, repeated=True)
            user.friends.append(friend2)
            user_obj.friends.append(friend1)
            user.put()
            user_obj.put()

        except Exception as e:
            logging.error(str(type(e)))
            logging.error(str(e))
            logging.error("User not found in the database: " + user.unique_user_name)
        self.redirect('/profile?')


class AcceptFriend(SessionsUsers.BaseHandler):
    def post(self):
        user_key = self.auth.get_user_by_session(save_session=True)
        user = DatabaseStructures.MUser.get_by_id(user_key['user_id'])
        user2 = self.request.get('user1')
        try:
            u2 = DatabaseStructures.MUser.query(DatabaseStructures.MUser.unique_user_name == user2).fetch(1)
            user_obj = u2[0]
            for friend in user.friends:
                if friend.username == user2:
                    friend.accepted = True
                    friend.pending = False
            for friend in user_obj.friends:
                if friend.username == user.unique_user_name:
                    friend.accepted = True
                    friend.pending = False
            user.put()
            user_obj.put()

        except Exception as e:
            logging.error(str(type(e)))
            logging.error(str(e))
            logging.error("User not found in the database: " + user.unique_user_name)
        self.redirect('/profile?')


class RemoveFriend(SessionsUsers.BaseHandler):
    def post(self):
        user_key = self.auth.get_user_by_session(save_session=True)
        user = DatabaseStructures.MUser.get_by_id(user_key['user_id'])
        user2 = self.request.get('user2')
        try:
            u2 = DatabaseStructures.MUser.query(DatabaseStructures.MUser.unique_user_name == user2).fetch(1)
            user_obj = u2[0]
            for friend in user.friends:
                if friend.username == user2:
                    user.friends.remove(friend)
            for friend in user_obj.friends:
                if friend.username == user.unique_user_name:
                    user_obj.friends.remove(friend)
            user.put()
            user_obj.put()
        except Exception as e:
            logging.error(str(type(e)))
            logging.error(str(e))
            logging.error("User not found in the database: " + user.unique_user_name)
        self.redirect('/profile?')


class SearchResults(SessionsUsers.BaseHandler):
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

        search = self.request.get('search_input')
        search_results = DatabaseStructures.MUser.query(search == DatabaseStructures.MUser.unique_user_name or
                                                        search == DatabaseStructures.MUser.display_name).fetch(1)
        if len(search_results) is 0:
            logging.error("user name didn't match anything")
            list_of_all_users = DatabaseStructures.MUser.query().fetch()
            for possible_match in list_of_all_users:
                if search in possible_match.unique_user_name:
                    search_results.append(possible_match)

        template_values = {"calendar": one_week_cal,
                           "user_name": user.unique_user_name,
                           "search_results": search_results,
                           }
        template = JINJA_ENVIRONMENT.get_template('SearchResults.html')
        self.response.write(template.render(template_values))


# returns the day indexed by character c
def decode_day(c):
    ascii_index = ord(c)
    index = ascii_index - 97
    day = DAYSOFTHEWEEK[index]
    return day


# takes a day of the week and returns character index
def encode_day(day):
    index = DAYSOFTHEWEEK.index(day)
    ascii_index = index + 97
    c = str(unichr(ascii_index))
    return c


# returns the start time of a particular block in 30 minute increments (1-48)
def decode_block(b):
    b -= 1
    hr = (b / 2) % 24
    minute = 0 if b % 2 is 0 else 30
    return datetime.time(hr, minute)


# returns the blocks between a given start time and end time
def encode_blocks(start, end):
    end -= datetime.timedelta(minutes=29, seconds=59)
    hour = start.hour
    minute = start.minute
    start_block = hour * 2 + (0 if minute is 0 else 1)

    hour = end.hour
    minute = end.minute
    end_block = hour * 2 + (0 if minute is 0 else 1)

    return range(start_block, end_block + 1)


class RecurringEvents(SessionsUsers.BaseHandler):
    def get(self):
        current_user = get_current_user(self)
        cal = current_user.user_recurring_calendar
        recurring_events = []
        blocks = []
        for day in DAYSOFTHEWEEK:
            for key in getattr(cal, day):
                recurring_events.append(key.get())

        template_values = { 'ids': recurring_events, 'first' : self.session.get('first') }

        for ev in recurring_events:
            day = encode_day(ev.day)
            block_nums = encode_blocks(ev.beginning_time, ev.ending_time)
            for b in block_nums:
                blocks.append(day + str(b))

        template_values = {"id": blocks}
        template = JINJA_ENVIRONMENT.get_template('recurring.html')
        self.response.write(template.render(template_values))

    def post(self):
        # blocks will have id in form
        pass

        current_user = get_current_user(self)

        # blocks will have id in form <letter (a-f) = day of week><number (1-48) = 30 min block>
        event_ids = self.request.get('id', allow_multiple=True)
        day_groups = {}
        # block_groups = {}

        for day_of_the_week in DAYSOFTHEWEEK:
            day_groups[day_of_the_week] = []
            # block_groups[day_of_the_week] = []

        # create dict of form dict[day] = list(blocks on that day)
        for ev in event_ids:
            day_char = str(ev[0])
            block_num = int(ev[1:])

            day = decode_day(day_char)
            day_groups[day].append(block_num)

        for key in day_groups.keys():
            block_nums = day_groups[key]

            block_groups = []
            start_block = None
            prev_block = None
            for block in block_nums:
                if not start_block:
                    start_block = block
                    prev_block = block
                if block is not prev_block + 1:
                    block_groups.append((start_block, prev_block))
                    start_block = block
                prev_block = block

            for start, end in block_groups:
                start_time = decode_block(start)
                end_time = decode_block(end) + datetime.timedelta(minutes=29, seconds=59)
                event = DatabaseStructures.Event(owner=current_user.unique_user_name,
                                                 beginning_time=start_time,
                                                 ending_time=end_time,
                                                 recurring=True)
                event_key = event.put()
                # ALERT. THIS MAY NOT WORK
                getattr(current_user.user_nonrecurring_calendar, key).append(event_key)
                # try this one instead if it doesn't work
                # current_user.user_nonrecurring_calendar[key].append(event_key)

        if self.session.get('first'):
            self.session['first'] = False
            self.session['message'] = 'Congratulations! You\'ve completed the signup'
        else:
            self.session['message'] = 'Recurring Calendar saved'
        
        self.redirect(self.uri_for('profile'))

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
            u = DatabaseStructures.MUser.get_by_id(inv)
            u.user_nonrecurring_calendar.events.append(event_key)
            u.put()
        event.updated = True
        event.put()


class EventHandler(SessionsUsers.BaseHandler):
    def get(self):
        user_key = self.auth.get_user_by_session(save_session=True)
        user = DatabaseStructures.MUser.get_by_id(user_key['user_id'])
        friends = user.friends
        template_values = {"friends": friends,
                           }
        template = JINJA_ENVIRONMENT.get_template('EventCreator.html')
        self.response.write(template.render(template_values))

    def post(self):
        current_user = get_current_user(self)
        title = self.request.get('title')
        location = self.request.get('location')
        description = self.request.get('description')
        invitees = self.request.get('invitees', allow_multiple=True)
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
        event.owner = current_user.unique_user_name

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

        current_user.user_nonrecurring_calendar.events.append(event_key)
        current_user.put()

        self.redirect("/profile")

        for inv in invitees:
            invitee = DatabaseStructures.Invitee(username=inv,
                                                 pending=True,
                                                 accepted=False,
                                                 timestamp=datetime.datetime.now(),
                                                 )
            event.attendees.append(invitee)
            u = DatabaseStructures.MUser.get_by_id(inv)

            if not current_user.user_nonrecurring_calendar:
                u.user_nonrecurring_calendar = DatabaseStructures.TemporaryCalendar()
            u.user_nonrecurring_calendar.events.append(event_key)
            u.put()

        event.put()

    def create(self):
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
            u = DatabaseStructures.MUser.get_by_id(inv)
            u.user_nonrecurring_calendar.events.append(event_key)
            u.put()
        event.updated = True

        event.put()
        self.redirect("/profile")


class UserHandler(SessionsUsers.BaseHandler):
    def get(self):
        pass

    def post(self):
        pass

webapp2_config = {'webapp2_extras.sessions': {'secret_key': 'secret_key_123', },
                  'webapp2_extras.auth': {'user_model': DatabaseStructures.MUser}
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
    webapp2.Route(r'/recurring', handler=RecurringEvents, name='recurring'),
    webapp2.Route(r'/search', handler=SearchResults, name="search"),
    webapp2.Route(r'/add/', handler=AddFriend, name='add-friend'),
    webapp2.Route(r'/remove/', handler=RemoveFriend, name='remove-friend'),
    webapp2.Route(r'/accept/', handler=AcceptFriend, name='accept-friend'),
    webapp2.Route(r'/test', handler=TestPage, name='test'),
], debug=True, config=webapp2_config)
