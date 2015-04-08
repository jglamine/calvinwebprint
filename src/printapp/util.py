from pymongo import MongoClient
from flask import request, session
from printapp import app

def get_current_user_credentials():
    """Returns the email and password of the currently signed in user.

    Information is read from the session cookie.
    Raises a ValueError if no session cookie has been set.
    """
    try:
        email = session['email']
        password = session['password']
    except KeyError:
        raise ValueError('No session cookie found.')

    return email, password
