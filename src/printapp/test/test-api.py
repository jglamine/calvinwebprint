import unittest
import os
import printapp
import flask
from printapp.api import _has_supported_filetype
import printapp.test.util

class ApiTestCase(unittest.TestCase):
    
    def setUp(self):
        printapp.app.secret_key = 'test key'
        printapp.app.config['TESTING'] = True
        self.get_client = printapp.app.test_client
        self.username = os.getenv('UNIFLOW_USER')
        self.password = os.getenv('UNIFLOW_PASSWORD')
        self.assertIsNotNone(self.username)
        self.assertIsNotNone(self.password)
        self._path = os.path.abspath(os.path.dirname(__file__))

    def test_get_index(self):
        with self.get_client() as app:
            response = app.get('/')
            self.assertEqual(self._status(response), 200)

    def test_login(self):
        with self.get_client() as app:
            response = app.post('/api/login')
            self.assertEqual(self._status(response), 400)
            self.assertIsNone(flask.session.get('email'))
            self.assertIsNone(flask.session.get('password'))

            form_data = {}
            form_data['email'] = '{}@students.calvin.edu'.format(self.username)
            form_data['password'] = self.password
            response = app.post('/api/login', data=form_data)
            self.assertEqual(self._status(response), 200)
            self.assertEqual(flask.session['email'], '{}@students.calvin.edu'.format(self.username))
            self.assertEqual(flask.session['password'], self.password)

            # test that whitespaces get stripped from the email
            form_data['email'] = '  {}@students.calvin.edu  '.format(self.username)
            response = app.post('/api/login', data=form_data)
            self.assertEqual(self._status(response), 200)
            self.assertEqual(flask.session['email'], '{}@students.calvin.edu'.format(self.username))

            form_data['email'] = 'invalid'
            form_data['password'] = 'invalid'
            response = app.post('/api/login', data=form_data)
            self.assertEqual(self._status(response), 401)
            self.assertIsNone(flask.session.get('email'))
            self.assertIsNone(flask.session.get('password'))

    @unittest.skipIf(printapp.test.util.is_cloudprint_api_key_missing(),
                 'no cloudprint api key found')
    def test_cloudprintstatus(self):
        with self.get_client() as app:
            response = app.get('/api/cloudprintstatus')
            self.assertEqual(self._status(response), 401)
            self.assertIsNone(flask.session.get('email'))
            self.assertIsNone(flask.session.get('password'))

            self._sign_in(app)

            response = app.get('/api/cloudprintstatus')
            response_json = flask.json.loads(response.data)
            self.assertEqual(self._status(response), 200)
            self.assertEquals(response_json['haveCloudPrintPermission'], True)
            self.assertEquals(response_json['isPrinterInstalled'], True)
            self.assertIsNotNone(response_json['cloudPrintPermissionUrl'])

    def test_uniflowstatus(self):
        with self.get_client() as app:
            response = app.get('/api/uniflowstatus')
            self.assertEqual(self._status(response), 401)
            self.assertIsNone(flask.session.get('email'))
            self.assertIsNone(flask.session.get('password'))

            self._sign_in(app)

            response = app.get("/api/uniflowstatus")
            response_json = flask.json.loads(response.data)
            self.assertEqual(self._status(response), 200)
            self.assertIsNotNone(response_json['queue'])
            self.assertIsNotNone(response_json['budget'])

    def test_upload_file(self):
        with self.get_client() as app:
            self._sign_in(app)

            for name in ['test.pdf', 'test.txt', 'test.doc', 'test.docx']:
                path = os.path.join(self._path, 'docs', name)
                test_file = open(path, 'rb')
                form_data = {}
                form_data['file'] = test_file
                response = app.post('/api/upload', data=form_data)
                response_json = flask.json.loads(response.data)
                self.assertEqual(self._status(response), 201)
                self.assertIsNotNone(response_json['file_id'])

            form_data = {}
            response = app.post('/api/upload', data=form_data)
            self.assertEqual(self._status(response), 400)

    def test_has_supported_filetype(self):
        self.assertFalse(_has_supported_filetype('test.file'))
        self.assertFalse(_has_supported_filetype('test.docc'))
        self.assertFalse(_has_supported_filetype('test.pddf'))
        self.assertTrue(_has_supported_filetype('test.doc'))
        self.assertTrue(_has_supported_filetype('test.docx'))
        self.assertTrue(_has_supported_filetype('test.pdf'))
        self.assertTrue(_has_supported_filetype('test.txt'))

    def _status(self, response):
        return int(response.status.split()[0])

    def _sign_in(self, app):
        form_data = {}
        form_data['email'] = '{}@students.calvin.edu'.format(self.username)
        form_data['password'] = self.password
        app.post('/api/login', data=form_data)


@unittest.skip("Skip test which actually prints.")
class ApiPrintDeleteTestCase(unittest.TestCase):
    def setUp(self):
        printapp.app.secret_key = 'test key'
        printapp.app.config['TESTING'] = True
        self.get_client = printapp.app.test_client
        self.username = os.getenv('UNIFLOW_USER')
        self.password = os.getenv('UNIFLOW_PASSWORD')
        self.assertIsNotNone(self.username)
        self.assertIsNotNone(self.password)
        self._path = os.path.abspath(os.path.dirname(__file__))

    def tearDown(self):
        """ Tests the /api/deletejob/<job_id> endpoint.
        """
        with self.get_client() as app:
            self._sign_in(app)

            response = app.post('/api/deletejob')
            self.assertEqual(self._status(response), 404)
            response = app.post('/api/deletejob/')
            self.assertEqual(self._status(response), 404)
            response = app.post('/api/deletejob/invalidJobID')
            self.assertEqual(self._status(response), 200)
            
            response = app.get("/api/uniflowstatus")
            response_json = flask.json.loads(response.data)
            self.assertEqual(self._status(response), 200)
            queue = response_json['queue']
            self.assertIsNotNone(queue)
            for document in queue:
                response = app.post('/api/deletejob/' + document['job_id'])
                self.assertEqual(self._status(response), 200)

            response = app.get("/api/uniflowstatus")
            response_json = flask.json.loads(response.data)
            self.assertEqual(response_json['queue'], [])

    def test_print(self):
        """Tests the /api/upload and /api/print endpoints.
        """
        with self.get_client() as app:
            self._sign_in(app)

            oid = []
            file_names = ['test.pdf', 'test.txt', 'test.doc', 'test.docx']
            for name in file_names:
                path = os.path.join(self._path, 'docs', name)
                test_file = open(path, 'rb')
                form_data = {}
                form_data['file'] = test_file
                response = app.post('/api/upload', data=form_data)
                response_json = flask.json.loads(response.data)
                objectid = response_json['file_id']
                oid.append(objectid)

            form_data = {}
            form_data['file_id'] = None
            form_data['color'] = True
            form_data['double_sided'] = 5
            form_data['collate'] = True
            form_data['copies'] = 1
            form_data['staple'] = True
            response = app.post('/api/print', data=form_data)
            self.assertEqual(self._status(response), 400)

            form_data['double_sided'] = False
            response = app.post('/api/print', data=form_data)
            self.assertEqual(self._status(response), 400)

            for objectid in oid:
                form_data['file_id'] = objectid
                response = app.post('/api/print', data=form_data)
                self.assertEqual(self._status(response), 201)

    def _status(self, response):
        return int(response.status.split()[0])

    def _sign_in(self, app):
        form_data = {}
        form_data['email'] = '{}@students.calvin.edu'.format(self.username)
        form_data['password'] = self.password
        app.post('/api/login', data=form_data)
