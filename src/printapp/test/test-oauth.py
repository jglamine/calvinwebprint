import unittest
import os
import webbrowser
import socket
import datetime
import oauth2client.client
import printapp.oauthcredentials as oauth
from printapp import app, mongo
import printapp.test.util

class TestOauth(unittest.TestCase):

    def setUp(self):
        self._email = 'testoauth@example.com'
        self._credentials = oauth2client.client.OAuth2Credentials(
                                access_token='token',
                                client_id='bar',
                                client_secret='bar',
                                refresh_token='refresh',
                                token_expiry=datetime.datetime.now() + datetime.timedelta(days=30),
                                token_uri='http://example.com',
                                user_agent='foo')
        with app.app_context():
            oauth._save_credentials(self._email, self._credentials)

    def test_get_code_from_url(self):
        with app.app_context():
            url = None
            self.assertRaises(ValueError, oauth.get_code_from_url, url)
            url = 'http://example.com'
            self.assertRaises(ValueError, oauth.get_code_from_url, url)
            url = 'http://example.com/?error=access_denied'
            self.assertRaises(ValueError, oauth.get_code_from_url, url)
            url = 'http://example.com/?code=HELLO'
            self.assertEqual(oauth.get_code_from_url(url), 'HELLO')

    def test_get_token(self):
        with app.app_context():
            token = oauth.get_token(self._email)
            self.assertIsNotNone(token)

    def test_delete_token(self):
        with app.app_context():
            oauth.delete_credentials(self._email, revoke=False)
            self.assertIsNone(oauth.get_token(self._email))

@unittest.skipIf(printapp.test.util.is_cloudprint_api_key_missing(),
                 'no cloudprint api key found')
class TestOauthFlow(unittest.TestCase):
    
    def setUp(self):
        self._email = None
        user = os.getenv('UNIFLOW_USER')
        self.assertNotEqual(None, user)
        self._email = '{}@students.calvin.edu'.format(user)

        with app.app_context():
            self._saved_credentials = oauth._get_credentials(self._email)
            oauth.delete_credentials(self._email, revoke=False)

    def tearDown(self):
        with app.app_context():
            oauth._save_credentials(self._email, self._saved_credentials)

    @unittest.skipIf(printapp.test.util.is_continuous_integration_server(),
                     'not run during continuous integration')
    def test_oauth_flow(self):
        with app.app_context():
            app.config['OAUTH_REDIRECT_URI'] = 'http://localhost:5000/oauthredirect'
            
            token = oauth.get_token(self._email)
            self.assertIsNone(token)
            url = oauth.get_authentication_prompt_url(self._email)
            self.assertIsNotNone(url)
        
            # open the oauth prompt url in a browser
            # start a web server and listen for the oauth callback
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind(('localhost', 5000))
            s.listen(1)
            s.settimeout(20)
            webbrowser.open(url)
            conn, addr = s.accept()
            conn.settimeout(20)
            try:
                response = conn.recv(4096)
            except socket.timeout:
                self.fail('Timeout while waiting for oauth callback')
            conn.send('HTTP/1.1 200 OK')
            conn.close()
            s.close()

            data = response.split()
            self.assertTrue(len(data) > 1)
            self.assertEqual(data[0], 'GET')
            url = data[1]
            url = 'http://example.com' + url
            access_code = oauth.get_code_from_url(url)

            token = oauth.authorize_user_by_code(access_code, self._email)
            token_from_db = oauth.get_token(self._email)
            self.assertEqual(token, token_from_db)
            
            credentials = oauth._get_credentials(self._email)
            self.assertIsNotNone(credentials)
            self._saved_credentials = oauth._get_credentials(self._email)

            credentials.token_expiry = datetime.datetime.now() - datetime.timedelta(minutes=15)
            oauth._save_credentials(self._email, credentials)
            
            # Check if the access token is getting refreshed correctly.
            token = oauth.get_token(self._email)
            self.assertIsNotNone(token)
            self._saved_credentials = oauth._get_credentials(self._email)
