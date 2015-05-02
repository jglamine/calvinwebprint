import unittest
import os
import json

class JsonTestCase(unittest.TestCase):
    
    def setUp(self):
		self._path = os.path.abspath(os.path.dirname(__file__))
		self.printers = open(os.path.join(self._path, '../static/', 'printers.json'))

    def test_printers_valid_json(self):
        try:
            json.load(self.printers)
        except ValueError as e:
            error_message = "printers.json is not in valid JSON format: {}".format(e)
            self.fail(error_message)
