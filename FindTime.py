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
    # daily_events = {}
    # event_blocks = {}

    def __init__(self, user):
        self.daily_events = {}
        for day in DAYSOFTHEWEEK:
            self.daily_events[day] = []
        if not user.user_recurring_calendar:
            user.user_recurring_calendar = DatabaseStructures.WeeklyRecurringSchedule()
        if not user.user_nonrecurring_calendar:
            user.user_nonrecurring_calendar = DatabaseStructures.TemporaryCalendar()

        recurring = user.user_recurring_calendar

        self.daily_events['monday'].extend(recurring.monday)
        self.daily_events['tuesday'].extend(recurring.tuesday)
        self.daily_events['wednesday'].extend(recurring.wednesday)
        self.daily_events['thursday'].extend(recurring.thursday)
        self.daily_events['friday'].extend(recurring.friday)
        self.daily_events['saturday'].extend(recurring.saturday)
        self.daily_events['sunday'].extend(recurring.sunday)
        nonrecurring = user.user_nonrecurring_calendar
        for event_key in nonrecurring.events:
            event = event_key.get()
            day = event.day
            day_index = day.weekday()
            day = DAYSOFTHEWEEK[day_index]
            self.daily_events[day].append(event_key)
        for key in self.daily_events:
            for ev in self.daily_events[key]:
                if not ev:
                    self.daily_events[key].remove(ev)

        self.event_blocks = {}
        for day in DAYSOFTHEWEEK:
            blocks = [None] * 48

            for ev_key in self.daily_events[day]:
                ev = ev_key.get()
                start = ev.beginning_time
                end = ev.ending_time
                block_range = encode_blocks(start, end)
                for b in block_range:
                    blocks[b] = (ev.key, ev.recurring, ev.event_name)
            self.event_blocks[day] = blocks

        self.time_decoding = {}
        midnight = datetime.datetime(100, 1, 1, 12, 0)
        for i in range(0, 48):
            if midnight.hour is 13:
                midnight = datetime.datetime(100, 1, 1, 1, 0)
            self.time_decoding[i] = str(midnight.time())
            midnight += datetime.timedelta(minutes=30)

    # more functionality to be added to this class based on javascript requirements


class ProfilePage(SessionsUsers.BaseHandler):
    def get(self, profile_id=None):
        current_user = get_current_user(self)
        if not profile_id:
            dest_user = current_user
        else:
            dest_user = DatabaseStructures.MUser.query(DatabaseStructures.MUser.unique_user_name == profile_id).fetch(1)[0]
        relation_state = None
        one_week_cal = None
        # friends_list = dest_user.friends
        # friends_list = dest_user.friends.query(DatabaseStructures.Friend.username == current_user.unique_user_name)\
        #                                 .fetch()
        friends_list = dest_user.friends

        #friend_behavior is an attribute used to route appropriate buttons for friend actions a user can take from anothers profile
        friend_behavior = (None, None)

        # dest_user.friends.query(DatabaseStructures.Friend.username == current_user.unique_user_name).fetch()
        # if not empty, grab first element
        if current_user.unique_user_name == dest_user.unique_user_name:
            relation_state = 'same_user'
            one_week_cal = Calendar(dest_user)
        else:
            relation_state = 'stranger'
            friend_behavior = ("/add/" + dest_user.unique_user_name, friend_behavior[1])
            for friend in friends_list:
                # ask stathi if accepted flag is required here******
                if friend.username == current_user.unique_user_name:
                    if friend.pending:
                        relation_state = 'cancel'
                        friend_behavior = ("/remove/" + dest_user.unique_user_name, friend_behavior[1])
                    else:
                        if friend.accepted:
                            relation_state = 'friend'
                            friend_behavior = ("/remove/" + dest_user.unique_user_name, friend_behavior[1])
                            one_week_cal = Calendar(dest_user)
                        else:
                            relation_state = 'accept/cancel'
                            friend_behavior = ("/accept/" + dest_user.unique_user_name, "/remove" + dest_user.unique_user_name)

        feed = []
        if relation_state is 'same_user':
            for friend in current_user.friends:
                if friend.pending:
                    friendTup = (friend, True, friend.timestamp)
                    feed.append(friendTup)
            for event_key in current_user.user_nonrecurring_calendar.events:
                event = event_key.get()
                for invitee in event.attendees:
                    if (invitee.username == current_user.unique_user_name) and (invitee.pending == True):
                        eventTup = (event, False, invitee.timestamp)
                        feed.append(eventTup)
        feed.sort(key=lambda x: x[2])

        logging.error(friends_list)
        logging.error(feed)

        template_values = {"calendar": one_week_cal,
                           "user_name": dest_user.unique_user_name,
                           "display_name": dest_user.display_name,
                           "friends": friends_list,
                           "relation": relation_state,
                           "feed": feed,
                           "friend_behavior": friend_behavior
                           }

        template = JINJA_ENVIRONMENT.get_template('Profile.html')

        self.response.write(template.render(template_values))

class EditEvents(SessionsUsers.BaseHandler):
    def post(self, unique_id=None, name=None, description=None, location=None):
        user_key = self.auth.get_user_by_session(save_session=True)
        user = DatabaseStructures.MUser.get_by_id(user_key['user_id'])
        event = DatabaseStructures.Event.get_by_id(int(unique_id))
        event.event_name = name
        event.event_location = location
        event.event_description = description
        event.put()




class AcceptInvite(SessionsUsers.BaseHandler):
    def post(self, unique_id=None):
        user_key = self.auth.get_user_by_session(save_session=True)
        user = DatabaseStructures.MUser.get_by_id(user_key['user_id'])
        event = DatabaseStructures.Event.get_by_id(int(unique_id))
        for invitee in event.attendees:
            if invitee.username == user.unique_user_name and invitee.pending ==True:
                invitee.pending = False
                invitee.accepted = True
        event.put()
        self.redirect('/profile?')

class RejectInvite(SessionsUsers.BaseHandler):
    def post(self, event):
        user_key = self.auth.get_user_by_session(save_session=True)
        user = DatabaseStructures.MUser.get_by_id(user_key['user_id'])
        for invitee in event.attendees:
            if invitee.username == user.unique_user_name and invitee.pending ==True:
                invitee.pending = False
                invitee.accepted = False
        event.put()
        self.redirect('/profile?')



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


#Matt's Friend Handler - handles add friend from their profile page
class AddFriend2(SessionsUsers.BaseHandler):
    def post(self, profile_id):
        user_key = self.auth.get_user_by_session(save_session=True)
        user = DatabaseStructures.MUser.get_by_id(user_key['user_id'])
        logging.error("$$$$$$$$$$$$$$$$$$$$$$" + profile_id)
        user2 = profile_id
        logging.error("$$$$$$$$$$$$$$$$$$$$$$" + user2)
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
        user2 = self.request.get('user')
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


#Matt's Accept Friend From Profile Page Handler
class AcceptFriend2(SessionsUsers.BaseHandler):
    def post(self, profile_id):
        user_key = self.auth.get_user_by_session(save_session=True)
        user = DatabaseStructures.MUser.get_by_id(user_key['user_id'])
        user2 = profile_id
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
        user2 = self.request.get('user')
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

#Matt's Remove Friend From Profile Page Handler
class RemoveFriend2(SessionsUsers.BaseHandler):
    def post(self, profile_id):
        user_key = self.auth.get_user_by_session(save_session=True)
        user = DatabaseStructures.MUser.get_by_id(user_key['user_id'])
        user2 = profile_id
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

        logging.error("%%%%%%%%%%%%%%%%" + self.request.get('search_input'))
        search = self.request.get('search_input')
        logging.error("%%%%%%%%%%%%%%%%" + search)

        search_results = DatabaseStructures.MUser.query(search == DatabaseStructures.MUser.unique_user_name or search == DatabaseStructures.MUser.display_name).fetch(1)


        logging.error(len(search_results))
        if len(search_results) is 0:
            logging.error("user name didn't match anything")
            list_of_all_users = DatabaseStructures.MUser.query().fetch()
            for possible_match in list_of_all_users:
                if search in possible_match.unique_user_name:
                    search_results.append(possible_match)

        newlist = []
        for res in search_results:
            newlist.append((res, '/profile/' + res.unique_user_name))
        search_results = newlist

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
    m = 0 if b % 2 is 0 else 30
    return datetime.datetime(100, 1, 1, hour=hr, minute=m)
    # return datetime.time(hr, minute)


# returns the blocks between a given start time and end time
def encode_blocks(start, end):
    end = (datetime.datetime(100, 1, 1, end.hour, end.minute) - datetime.timedelta(minutes=29, seconds=59)).time()
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
        if not current_user.user_recurring_calendar:
            current_user.user_recurring_calendar = DatabaseStructures.WeeklyRecurringSchedule()
        cal = current_user.user_recurring_calendar
        recurring_events = []
        blocks = []
        for day in DAYSOFTHEWEEK:
            for key in getattr(cal, day):
                recurring_events.append(key.get())

        for ev in recurring_events:
            if ev:
                day = encode_day(ev.recurring_day)
                block_nums = encode_blocks(ev.beginning_time, ev.ending_time)
                for b in block_nums:
                    blocks.append(day + str(b))
        if len(blocks) is 0:
            template_values = {"ids": [], 'first': self.session.get('first')}
        template_values = {"ids": blocks, 'first': self.session.get('first')}
        template = JINJA_ENVIRONMENT.get_template('recurring.html')
        self.response.write(template.render(template_values))

    def post(self):
        # blocks will have id in form
        current_user = get_current_user(self)
        if not current_user.user_recurring_calendar:
            current_user.user_recurring_calendar = DatabaseStructures.WeeklyRecurringSchedule()
        logging.error("before: " + str(current_user.user_recurring_calendar))
        for day in DAYSOFTHEWEEK:
            del getattr(current_user.user_recurring_calendar, day)[:]
        logging.error("after: " + str(current_user.user_recurring_calendar))
        # blocks will have id in form <letter (a-f) = day of week><number (1-48) = 30 min block>
        event_ids = []
        e = self.request.get('id')
        event_strings = str(e).split('&')
        for ev in event_strings:
            unused, event_string = ev.split('=')
            event_ids.append(event_string)
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
                elif block is not prev_block + 1:
                    block_groups.append((start_block, prev_block))
                    start_block = block
                elif block is block_nums[-1]:
                    block_groups.append((start_block, block))
                prev_block = block
            for start, end in block_groups:
                numblocks = end - start + 1
                start_time = decode_block(start).time()
                end_time = (decode_block(end) + datetime.timedelta(minutes=29, seconds=59)).time()
                event = DatabaseStructures.Event(owner=current_user.unique_user_name,
                                                 beginning_time=start_time,
                                                 ending_time=end_time,
                                                 recurring=True,
                                                 num_blocks=numblocks,
                                                 recurring_day=key)
                event_key = event.put()
                getattr(current_user.user_recurring_calendar, key).append(event_key)
        current_user.put()
        if self.session.get('first'):
            self.session['first'] = False
            self.session['message'] = 'Congratulations! You\'ve completed the signup'
        else:
            self.session['message'] = 'Recurring Calendar saved'
        
        return self.redirect(self.uri_for('profile-self'))


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


class EventView(SessionsUsers.BaseHandler):
    def get(self, unique_id):
        event = DatabaseStructures.Event.get_by_id(int(unique_id))
        invitees = event.attendees
        attendees = [e for e in invitees if e.accepted]
        if event.recurring:
            template_values = {'title': "Recurring event",
                               'owner': "",
                               'description': "",
                               'location': "",
                               'day': event.recurring_day,
                               'start_time': event.beginning_time,
                               'end_time': event.ending_time,
                               'attendees': [],
                                }
        else:
            template_values = {'title': event.event_name,
                               'owner': event.owner,
                               'description': event.event_description,
                               'location': event.event_location,
                               'day': event.day,
                               'start_time': event.beginning_time,
                               'end_time': event.ending_time,
                               'attendees': attendees,
                               }

        template = JINJA_ENVIRONMENT.get_template('ViewEvent.html')
        self.response.write(template.render(template_values))


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
        num_hr = end_hr - start_hr
        num_min = end_min - start_min
        num_blocks = num_hr * 2 + num_min / 30
        event.num_blocks = num_blocks


        event_key = event.put()

        current_user.user_nonrecurring_calendar.events.append(event_key)
        current_user.put()

        for inv in invitees:
            invitee = DatabaseStructures.Invitee(username=inv,
                                                 pending=True,
                                                 accepted=False,
                                                 timestamp=datetime.datetime.now(),
                                                 )
            event.attendees.append(invitee)
            u2 = DatabaseStructures.MUser.query(DatabaseStructures.MUser.unique_user_name == inv).fetch(1)
            u = u2[0]
            if not u.user_nonrecurring_calendar:
                u.user_nonrecurring_calendar = DatabaseStructures.TemporaryCalendar()

            u.user_nonrecurring_calendar.events.append(event_key)
            u.put()

        event.put()

        self.redirect("/profile")

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
    webapp2.Route(r'/profile', handler=ProfilePage, name="profile-self"),
    webapp2.Route(r'/profile/<profile_id>', handler=ProfilePage, name="profile"),
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
    webapp2.Route(r'/add/<profile_id>', handler=AddFriend2, name='add-friend'),
    webapp2.Route(r'/remove/', handler=RemoveFriend, name='remove-friend'),
    webapp2.Route(r'/remove/<profile_id>', handler=RemoveFriend2, name='remove-friend'),
    webapp2.Route(r'/accept/', handler=AcceptFriend, name='accept-friend'),
    webapp2.Route(r'/accept/<profile_id>', handler=AcceptFriend2, name='accept-friend'),
    webapp2.Route(r'/test', handler=TestPage, name='test'),
    webapp2.Route(r'/event/view/<unique_id>', handler=EventView, name='view-event'),
    webapp2.Route(r'/acceptinvite', handler=AcceptInvite, name='acceptinvite'),
    webapp2.Route(r'/acceptinvite/<unique_id>', handler=AcceptInvite, name='acceptinvite'),
    webapp2.Route(r'/rejectinvite', handler=RejectInvite, name='rejectinvite'),
    webapp2.Route(r'/edit/<unique_id>&<name>&<description>&<location>', handler=EditEvents, name='edit'),
], debug=True, config=webapp2_config)
