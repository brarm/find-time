import jinja2
import webapp2

import os
import urllib

from google.appengine.api import users
from google.appengine.ext import ndb


class Event(ndb.Model):
    """Individual time block (30 min minimum) to be stored in calendars"""
    # beginning_day = ndb.DateProperty(indexed=True)
    beginning_day = ndb.StringProperty(indexed=True)
    beginning_time = ndb.TimeProperty(indexed=True)
    # ending_day = ndb.DateProperty(indexed=True)
    ending_day = ndb.StringProperty(indexed=True)
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
    tuesday = ndb.StructuredProperty(Event, repeated=True)
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