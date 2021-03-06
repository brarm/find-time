import jinja2
import webapp2

import os
import urllib

from google.appengine.api import users
import datetime

from google.appengine.ext import ndb
import webapp2_extras.appengine.auth.models as auth_models


class Invitee(ndb.Model):
    username = ndb.StringProperty(indexed=False)
    pending = ndb.BooleanProperty(indexed=True)
    accepted = ndb.BooleanProperty(indexed=False)
    updated = ndb.BooleanProperty(default=False, indexed=True)
    timestamp = ndb.DateTimeProperty(indexed=True)


class Friend(ndb.Model):
    username = ndb.StringProperty(indexed=True)
    pending = ndb.BooleanProperty(indexed=True)
    accepted = ndb.BooleanProperty(indexed=True)
    timestamp = ndb.DateTimeProperty(indexed=True)


class Event(ndb.Model):
    """Individual time block (30 min minimum) to be stored in calendars"""
    owner = ndb.StringProperty(indexed=True)
    attendees = ndb.StructuredProperty(Invitee, indexed=True, repeated=True)
    day = ndb.DateProperty(indexed=True)
    beginning_time = ndb.TimeProperty(indexed=True)
    ending_time = ndb.TimeProperty(indexed=True)
    event_name = ndb.StringProperty(indexed=False)
    event_location = ndb.StringProperty(indexed=False)
    event_description = ndb.TextProperty(indexed=False)
    recurring = ndb.BooleanProperty(indexed=False, default=False)
    recurring_day = ndb.StringProperty(indexed=True)
    num_blocks = ndb.IntegerProperty(indexed=False)


class WeeklyRecurringSchedule(ndb.Model):
    """Model for a 7 day calendar for a particular user"""
    sunday = ndb.KeyProperty(Event, repeated=True)
    monday = ndb.KeyProperty(Event, repeated=True)
    tuesday = ndb.KeyProperty(Event, repeated=True)
    wednesday = ndb.KeyProperty(Event, repeated=True)
    thursday = ndb.KeyProperty(Event, repeated=True)
    friday = ndb.KeyProperty(Event, repeated=True)
    saturday = ndb.KeyProperty(Event, repeated=True)


class TemporaryCalendar(ndb.Model):
    events = ndb.KeyProperty(Event, repeated=True)


class MUser(auth_models.User):
    """Model for representing an individual user."""
    unique_user_name = ndb.StringProperty(indexed=True)
    display_name = ndb.StringProperty(indexed=False)
    email_address = ndb.StringProperty(indexed=False)
    user_nonrecurring_calendar = ndb.StructuredProperty(TemporaryCalendar, repeated=False)
    user_recurring_calendar = ndb.StructuredProperty(WeeklyRecurringSchedule, repeated=False)
    friends = ndb.StructuredProperty(Friend, indexed=False, repeated=True)
