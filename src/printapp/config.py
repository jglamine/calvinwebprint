MONGO_URL = 'mongodb://localhost:27017/webprint'
PRINTPRICES = [
	{'name': 'mfd-single-sided', 'black': 0.0255, 'color': 0.255},
	{'name': 'mfd-double-sided', 'black': 0.0205, 'color': 0.25},
	{'name': 'laser-single-sided', 'black': 0.0285, 'color': 0.285},
	{'name': 'laser-double-sided', 'black': 0.0235, 'color': 0.28}
]

LOGFILE = 'calvinwebprint.log'

# Override these in a configuration file, then set the `PRINTAPP_SETTINGS`
# environment variable to that file.
# If these variables are not set, communication with google cloud print will
# not work and relevant tests will be disabled.
OAUTH_CLIENT_ID = None
OAUTH_CLIENT_SECRET = None
OAUTH_REDIRECT_URI = 'http://localhost:5001/oauthredirect' # change in production

# Used to encrypt session cookies. Override this in production.
SECRET_KEY = 'this is not a secret'
