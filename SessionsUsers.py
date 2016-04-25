import logging
import webapp2
import DatabaseStructures
from webapp2_extras import auth
from webapp2_extras import sessions
from webapp2_extras.auth import InvalidAuthIdError
from webapp2_extras.auth import InvalidPasswordError


def user_required(handler):
    """
         Decorator for checking if there's a user associated with the current session.
         Will also fail if there's no session present.
     """

    def check_login(self, *args, **kwargs):
        auth = self.auth
        if not auth.get_user_by_session():
            # If handler has no login_url specified invoke a 403 error
            try:
                self.redirect(self.auth_config['login_url'], abort=True)
            except (AttributeError, KeyError), e:
                self.abort(403)
        else:
            return handler(self, *args, **kwargs)

    return check_login


class BaseHandler(webapp2.RequestHandler):
    """
         BaseHandler for all requests

         Holds the auth and session properties so they are reachable for all requests
     """

    def dispatch(self):
        """
              Save the sessions for preservation across requests
          """
        try:
            response = super(BaseHandler, self).dispatch()
            self.response.write(response)
        finally:
            self.session_store.save_sessions(self.response)

    @webapp2.cached_property
    def auth(self):
        return auth.get_auth()

    @webapp2.cached_property
    def session_store(self):
        return sessions.get_store(request=self.request)

    @webapp2.cached_property
    def auth_config(self):
        """
              Dict to hold urls for login/logout
          """
        return {
            'login_url': self.uri_for('login'),
            'logout_url': self.uri_for('logout')
        }


class LoginHandler(BaseHandler):
    def get(self):
        """
              Returns a simple HTML form for login
          """
        return """
			<!DOCTYPE hml>
			<html>
				<head>
					<title>webapp2 auth example</title>
				</head>
				<body>
				<form action="%s" method="post">
					<fieldset>
						<legend>Login form</legend>
						<label>Username <input type="text" name="username" placeholder="Your username" /></label>
						<label>Password <input type="password" name="password" placeholder="Your password" /></label>
					</fieldset>
					<button>Login</button>
				</form>
			</html>
		""" % self.request.url

    def post(self):
        """
              username: Get the username from POST dict
              password: Get the password from POST dict
          """
        username = self.request.POST.get('username')
        password = self.request.POST.get('password')
        # Try to login user with password
        # Raises InvalidAuthIdError if user is not found
        # Raises InvalidPasswordError if provided password doesn't match with specified user
        try:
            logging.error("log 1")
            self.auth.get_user_by_password(username, password, save_session=True)
            logging.error("log 1a")
            self.redirect('/secure')
            logging.error("log 1b")
        except (InvalidAuthIdError, InvalidPasswordError), e:
            logging.error("log 2")
            # Returns error message to self.response.write in the BaseHandler.dispatcher
            # Currently no message is attached to the exceptions
            return e
        logging.error("Should be redirecting now")
        self.redirect('/?')


class CreateUserHandler(BaseHandler):
    def get(self):
        """
              Returns a simple HTML form for create a new user
          """
        return """
			<!DOCTYPE hml>
			<html>
				<head>
					<title>webapp2 auth example</title>
				</head>
				<body>
				<form action="%s" method="post">
					<fieldset>
						<legend>Create user form</legend>
						<label>Username <input type="text" name="username" placeholder="Your username" /></label>
						<label>Password <input type="password" name="password" placeholder="Your password" /></label>
					</fieldset>
					<button>Create user</button>
				</form>
			</html>
		""" % self.request.url

    def post(self):
        """
              username: Get the username from POST dict
              password: Get the password from POST dict
          """
        username = self.request.POST.get('username')
        password = self.request.POST.get('password')
        # Passing password_raw=password so password will be hashed
        # Returns a tuple, where first value is BOOL. If True ok, If False no new user is created
        tempcal = DatabaseStructures.TemporaryCalendar()
        weekcal = DatabaseStructures.WeeklyRecurringSchedule()
        email = "balls.com"
        friends = []
        user = self.auth.store.user_model.create_user(username, password_raw=password, unique_user_name=username,
                                                      temporary_calendar=tempcal, weekly_recurring_schedule=weekcal,
                                                      email_address=email, friends=friends)
        if not user[0]: #user is a tuple
            return user[1] # Error message
        else:
            # User is created, let's try redirecting to login page
            try:
                self.redirect(self.auth_config['login_url'], abort=True)
            except (AttributeError, KeyError), e:
                self.abort(403)


class LogoutHandler(BaseHandler):
    """
         Destroy user session and redirect to login
     """

    def get(self):
        self.auth.unset_session()
        # User is logged out, let's try redirecting to login page
        try:
            self.redirect(self.auth_config['login_url'])
        except (AttributeError, KeyError), e:
            return "User is logged out"


class SecureRequestHandler(BaseHandler):
    """
         Only accessible to users that are logged in
     """

    @user_required
    def get(self, **kwargs):
        logging.error("log 4")
        user = self.auth.get_user_by_session()
        try:
            logging.error("log 3")
            return "Secure zone for %s <a href='%s'>Logout</a>" % (str(user), self.auth_config['logout_url'])
        except (AttributeError, KeyError), e:
            logging.error("log 4")
            return "Secure zone"