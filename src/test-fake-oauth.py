import unittest
from fakeoauth import add_fake_credentials
from printapp import app, mongo, oauthcredentials

class TestFakeOauth(unittest.TestCase):

    def setUp(self):
        self._email = 'unittestuser'

    def test_add_user(self):
        with app.app_context():
            mongo.db.credentials.remove({'email': self._email})
            result = mongo.db.credentials.find_one({'email': self._email})
            self.assertIsNone(result)

        add_fake_credentials(self._email)

        with app.app_context():
            result = mongo.db.credentials.find_one({'email': self._email})
            self.assertIsNotNone(result)
            credentials = oauthcredentials.get_token(self._email)
            self.assertIsNotNone(credentials)
