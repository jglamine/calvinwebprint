import unittest
import os
import time
import printapp.oauthcredentials
import printapp.client
import printapp.auth
import printapp.cloudprint
import printapp.test.util
from printapp import app

UNIFLOW_ID = 'eeec5cdd-8deb-e24a-8f04-30bf0447b555'

@unittest.skipIf(printapp.test.util.is_cloudprint_api_key_missing(),
                 'no cloudprint api key found')
class TestCloudprint(unittest.TestCase):

    def setUp(self):
        user = os.getenv('UNIFLOW_USER')
        self.assertNotEqual(None, user)
        self._email = '{}@students.calvin.edu'.format(user)
        self._path = os.path.abspath(os.path.dirname(__file__))

        with app.app_context():
            self._token = printapp.oauthcredentials.get_token(self._email)
            self.assertIsNotNone(self._token)
    
    def test_has_uniflow_printer(self):
        with app.app_context():
            result = printapp.cloudprint.has_uniflow_printer(token=self._token)
            self.assertEqual(result, True)

    def test_make_ticket(self):
        with app.app_context():
            ticket1 = printapp.cloudprint._make_print_ticket()
            self.assertIsNotNone(ticket1)
            ticket2 = printapp.cloudprint._make_print_ticket(False, False, 1, True)
            self.assertIsNotNone(ticket2)
            self.assertEqual(ticket1, ticket2)
            ticket3 = printapp.cloudprint._make_print_ticket(True, True, 12, True)
            self.assertIsNotNone(ticket3)
            ticket4 = printapp.cloudprint._make_print_ticket(color=True, duplex=True,
                                                             copies=12, collate=False)
            self.assertIsNotNone(ticket4)
            self.assertNotEqual(ticket3, ticket4)
            ticket5 = printapp.cloudprint._make_print_ticket(collate=True)
            self.assertIsNotNone(ticket5)
            self.assertEqual(ticket1, ticket5)

    @unittest.skip("Tests which actually print are disabled.")
    def test_submit_job(self):
        """Test submitting jobs to uniflow.

        This test is disabled by default. Uncomment the decorator above
        to enable it.
        """

        with app.app_context():
            file_names = ['test.pdf', 'test.txt', 'test.doc', 'test.docx']
            for name in file_names:
                path = os.path.join(self._path, 'docs', name)
                test_file = open(path, 'rb')
                printapp.cloudprint.submit_job(self._token, test_file,
                                               color=False, duplex=True,
                                               copies=1, collate=False)
                test_file.close()
