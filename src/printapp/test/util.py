import unittest
import os
from printapp import app

def is_continuous_integration_server():
    """Returns True if python is running on a continuous integration server.

    True if the 'JENKINS_CI' environment variable is set.
    """
    return os.environ.get('JENKINS_CI') is not None

def is_cloudprint_api_key_missing():
    """Returns True if settings for the google cloud print api are missing.
    """
    return None in (app.config['OAUTH_CLIENT_ID'],
                    app.config['OAUTH_CLIENT_SECRET'],
                    app.config['OAUTH_REDIRECT_URI'])
