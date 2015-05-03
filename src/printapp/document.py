from datetime import datetime
import pymongo
import gridfs
from printapp import mongo
from bson.objectid import ObjectId


def delete_document(document_id, email):
    """Deletes a document by document_id.

    Raises DatabaseError on error.
    """
    document_id = ObjectId(document_id)
    try:
        fs = gridfs.GridFS(mongo.db, 'document_fs')
    except TypeError as err:
        raise DatabaseError(err)

    if fs.exists(_id=document_id, email=email):
        fs.delete(document_id)


def get_document(document_id, email):
    """Retrieves a document by document_id.

    Returns an open file-like object.
    Returns None if no such file exists for the given email.

    Raises DatabaseError on error.
    """
    document_id = ObjectId(document_id)
    try:
        fs = gridfs.GridFS(mongo.db, 'document_fs')
    except TypeError as err:
        raise DatabaseError(err)
    
    if fs.exists(_id=document_id, email=email):
        file_handle = fs.get(document_id)
        return file_handle


def save_document(file_handle, document_name, email):
    """Saves a document for later printing, returning the document_id.

    file_handle - a handle to an open file-like object.

    Each user can store at most five documents. Old documents are deleted to
    make room for new documents.

    Raises DatabaseError on error.
    """
    try:
        fs = gridfs.GridFS(mongo.db, 'document_fs')
    except TypeError as err:
        raise DatabaseError(err)

    # Remove old documents until only 4 remain.
    try:
        documents = fs.find( {'email': email } ).sort('timestamp', pymongo.DESCENDING).skip(4)
    except TypeError as err:
        raise DatabaseError(err)
    for document in documents:
        fs.delete(document._id)

    document_id = fs.put(file_handle, email=email, filename=document_name,
                         timestamp=datetime.now())
    return str(document_id)

class DatabaseError(Exception):
    pass
