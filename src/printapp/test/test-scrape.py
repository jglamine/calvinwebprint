import unittest
import os
from printapp.printstatus import *

class TestPrintQueue(unittest.TestCase):

    def setUp(self):
        self.username = os.getenv('UNIFLOW_USER')
        self.password = os.getenv('UNIFLOW_PASSWORD')
        self.assertNotEqual(None, self.username)
        self.assertNotEqual(None, self.password)

    def test_budget(self):
        uc = get_uniflow_client(self.username, self.password)
        budget = uc.get_budget()
        self.assertIsInstance(budget, float)
        budget = uc.get_budget()
        self.assertIsInstance(budget, float)

    def test_queue(self):
        uc = get_uniflow_client(self.username, self.password)
        uc.get_print_queue()
        uc.get_print_queue()

    def test_invalid_credentials(self):
        self.assertRaises(InvalidCredentialsError, get_uniflow_client,
                          'invalidUser', 'invalidPassword')

    def test_blank_credentials(self):
        self.assertRaises(InvalidCredentialsError, get_uniflow_client,
                          '', '')
        self.assertRaises(InvalidCredentialsError, get_uniflow_client,
                          'invalidUser', '')
        self.assertRaises(InvalidCredentialsError, get_uniflow_client,
                          '', 'invalidPassword')
