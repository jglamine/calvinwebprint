#!/usr/bin/env python
# Adds fake oauth credentials to the database.
# For testing purposes when google cloud print API tokens are not available.

import sys
from oauth2client.client import OAuth2Credentials
from printapp import app, mongo, oauthcredentials

def add_fake_credentials(email, hasprinter=True):
    token = 'fakeoauth.py|noprinter'
    if hasprinter:
        token = 'fakeoauth.py'
    credentials = OAuth2Credentials(token, token, token,
                                    token, None, token, token)

    with app.app_context():
        oauthcredentials._save_credentials(email, credentials)

def remove_credentials(email):
    with app.app_context():
        mongo.db.credentials.remove({'email': email})
    
if __name__ == '__main__':
    usage = 'Usage: {} username [delete|noprinter]'.format(sys.argv[0])
    if len(sys.argv) not in (2, 3):
        print usage
    else:
        if len(sys.argv) == 3:
            command = sys.argv[2]
        else:
            command = 'add'

        email = sys.argv[1]
        if '@' not in email:
            email = email + '@students.calvin.edu'

        if command == 'add':
            add_fake_credentials(email)
        elif command == 'noprinter':
            add_fake_credentials(email, hasprinter=False)
        elif command in ('delete', 'remove') :
            remove_credentials(email)
        else:
            print usage
