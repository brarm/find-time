import os
import urllib

from google.appengine.api import users
from google.appengine.ext import ndb

import jinja2
import webapp2

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

# find-time classes
class Event(ndb.Model):
    """Individual time block (30 min minimum) to be stored in calendars"""
    beginning_day = ndb.DateProperty(indexed=True)
    beginning_time = ndb.TimeProperty(indexed=True)
    ending_day = ndb.DateProperty(indexed=True)
    ending_time = ndb.TimeProperty(indexed=True)
    is_free_time = ndb.BooleanProperty(default=False)
    event_name = ndb.StringProperty(indexed=False)
    event_location = ndb.StringProperty(indexed=False)
    event_description = ndb.TextProperty(indexed=False)


class TemporaryCalendar(ndb.Model):
    events = ndb.StructuredProperty(Event, repeated=True)


class WeeklyRecurringSchedule(ndb.Model):
    """Model for a 7 day calendar for a particular user"""
    sunday = ndb.StructuredProperty(Event, repeated=True)
    monday = ndb.StructuredProperty(Event, repeated=True)
    wednesday = ndb.StructuredProperty(Event, repeated=True)
    thursday = ndb.StructuredProperty(Event, repeated=True)
    friday = ndb.StructuredProperty(Event, repeated=True)
    saturday = ndb.StructuredProperty(Event, repeated=True)


class User(ndb.Model):
    """Model for representing an individual user."""
    unique_user_name = ndb.StringProperty(indexed=True)
    display_name = ndb.StringProperty(indexed=False)
    email_address = ndb.StringProperty(indexed=False)
    user_nonrecurring_calendar = ndb.StructuredProperty(TemporaryCalendar, repeated=False)
    user_recurring_calendar = ndb.StructuredProperty(WeeklyRecurringSchedule, repeated=False)
    friends = ndb.StringProperty(indexed=False, repeated=True)
    # notifications = ndb.StructuredProperty(Notification, repeated=True)


class Notification(ndb.Model):
    notification_type = ndb.StringProperty(indexed=True)
    user_notified = ndb.StructuredProperty(User)
    user_instigating = ndb.StructuredProperty(User)
    notification_body = ndb.StringProperty(indexed=False)
    event_associated = ndb.StructuredProperty(Event, default=None)
    title = ndb.StringProperty(indexed=False)


class MainPage(webapp2.RequestHandler):
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

        template_values = {
            'user': user,
            'greetings': greetings,
            'guestbook_name': urllib.quote_plus(guestbook_name),
            'url': url,
            'url_linktext': url_linktext,
        }
        #
        # user = User()
        # user.display_name = "Matt"
        # user.put()

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

class EventPage(webapp2.RequestHandler):
    def get(self):
        template = JINJA_ENVIRONMENT.get_template('EventCreator.html')
        self.response.write(template.render())

class EventCreator(webapp2.RequestHandler):
    def post(self):
        event = Event()
        event.event_name = self.request.get("title")
        event.event_location = self.request.get("location")
        event.event_description = self.request.get("description")
        event.put()

        guestbook_name = self.request.get('guestbook_name',
                                          DEFAULT_GUESTBOOK_NAME)
        query_params = {'guestbook_name': guestbook_name}
        self.redirect('/?' + urllib.urlencode(query_params))

app = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/sign', Guestbook),
    ('/event_page', EventPage),
    ('/create_event', EventCreator),
], debug=True)