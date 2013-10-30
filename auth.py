# Copyright (C) 2012 SCS srl <info@scsitaly.com>

""" This module contains all authentication related functions. It imports the authentication application basic
functionalities to create and validate the authentication tickets. """


import urllib2

try:
    import json
except ImportError:
    import simplejson as json

from functools import wraps
from flask import request, Response


AUTH_SERVER_URL = "http://devauth.biomedtown.org/"
TKT_VALIDATION_SERVER_URL = "http://devel.vph-share.eu/"


def checkAuthentication(username, password):
    """ This function is called to check if a username password combination is valid.

    Arguments:
        username (string): the user identifier
        password (string): the user password

    Returns:
        boolean. True if the authentication check is successful, False otherwise

    """

    # get the ticket
    if getAuthTicket(username, password) is not None:
        return True

    return False


def getAuthTicket(username, password):
    """ Returns the authentication ticket for given username.

    Arguments:
        secret (string): the secret key to be used to produce the authentication ticket
        username (string): the username the ticket has to be produced for

    Returns:
        string. The authentication ticket as a string

    """

    resp = urllib2.urlopen('%s/user_login?domain=VPHSHARE&username=%s&password=%s' % (AUTH_SERVER_URL, username, password))
    ticket = resp.read()

    if resp.code != 200:
        return None

    return ticket


def extractUserFromTicket(ticket):
    """ Extracts the user dictionary from the given authentication ticket.

    Arguments:
        ticket (string): the authentication ticket

    Returns:
        dictionary. the extracted user attributes as a dictionary

    """
    try:
        resp = urllib2.urlopen('%svalidatetkt/?ticket=%s' % (TKT_VALIDATION_SERVER_URL, ticket))
        user_dict = json.loads(resp.read())
        return user_dict
    except BaseException, e:
        pass

    return None


def authenticate():
    """Sends a 401 response that enables basic auth"""
    return Response(
    'Could not verify your access level for that URL.\n'
    'You have to login with proper credentials', 401,
    {'WWW-Authenticate': 'Basic realm="Login Required"'})


def requiresAuthentication(f):
    """ Function decorator. User must be logged in order to call the decorated method.

    Arguments:
        f (function): the function to be decorated

    Returns:
        function. Retursn the decorated function

    """
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not checkAuthentication(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated