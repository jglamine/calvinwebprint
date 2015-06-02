import unittest
import os
import flask
import gridfs
import printapp
from printapp import app, mongo
from printapp.document import save_document, get_document, delete_document
from bson.objectid import ObjectId

class TestDocument(unittest.TestCase):

    def setUp(self):
        user = os.getenv('UNIFLOW_USER')
        self.assertNotEqual(None, user)
        self._email = 'test@example.com'
        self._path = os.path.abspath(os.path.dirname(__file__))

    def test_delete_document(self):
        with app.app_context():
            file_name = 'test.docx'
            path = os.path.join(self._path, 'docs', file_name)
            with open(path, 'rb') as test_file:
                _id = save_document(file_handle=test_file,
                                    document_name=file_name, email=self._email)
            self.assertIsNotNone(_id)
            delete_document(_id, self._email)

            retrieved_file = get_document(document_id=_id, email=self._email)
            self.assertIsNone(retrieved_file)
    
    def test_get_and_save_document(self):
        with app.app_context():
            file_name = 'test.docx'
            path = os.path.join(self._path, 'docs', file_name)
            with open(path, 'rb') as test_file:
                _id = save_document(file_handle=test_file, 
                                    document_name=file_name, email=self._email)

            self.assertIsNotNone(_id)
            retrieved_file = get_document(document_id=_id, email=self._email)
            retrieved_data = retrieved_file.read()

            with open(path, 'rb') as test_file:
                expected_data = test_file.read()
                self.assertEqual(len(expected_data), len(retrieved_data))
                self.assertTrue(expected_data == retrieved_data)
    
    def test_save_document(self):
        """Test that only the five most recent uploaded items per user
        are saved in the database.
        """
        with app.app_context():
            fs = gridfs.GridFS(mongo.db, 'document_fs')
            documents = fs.find( {'email': self._email } )
            for document in documents:
                fs.delete(document._id)

            count = 0
            documents = fs.find( {'email': self._email } )
            for doc in documents:
                count += 1
            self.assertEqual(count, 0)

            file_name = 'a.txt'
            path = os.path.join(self._path, 'docs', file_name)
            doc_ids = []
            for i in range(7):
                with open(path, 'rb') as test_file:
                    _id = save_document(file_handle=test_file, 
                                        document_name=file_name, email=self._email)
                    self.assertIsNotNone(_id)
                    doc_ids.append(_id)

            count = 0
            documents = fs.find( {'email': self._email } )
            for doc in documents:
                count += 1
            self.assertEqual(count, 3)

            for i in range(2):
                self.assertFalse(fs.exists(_id=ObjectId(doc_ids[i]), email=self._email))
