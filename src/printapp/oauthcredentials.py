import urlparse
import json
import os
import requests
import httplib2
from urllib import urlencode
from pymongo.errors import PyMongoError
import oauth2client.client as oauth
from printapp import mongo, app

def get_token(email):
    """Fetches the authorization token for the given email address.

    Returns None if no token is present.

    See google's oauth documentation for details:
    https://developers.google.com/accounts/docs/OAuth2
    """
    credentials = _get_credentials(email)
    if credentials is None:
        return None

    if credentials.access_token_expired:
        try:
            credentials.refresh(httplib2.Http())
        except oauth.AccessTokenRefreshError:
            delete_credentials(email)
            return None
        except oauth.Error as err:
            raise WebServiceError(err)
        
        try:
            _save_credentials(email, credentials)
        except PyMongoError as err:
            raise WebServiceError(err)

    return credentials.access_token

def get_authentication_prompt_url(email):
    """A user can grant access to their cloudprint account by visiting this URL.

    This is the first step of the oauth process.
    See google's oauth documentation for details:
    https://developers.google.com/accounts/docs/OAuth2
    """
    flow = _get_flow()
    authorize_url = flow.step1_get_authorize_url()
    authorize_url = _add_query_param(authorize_url, 'login_hint', email)
    authorize_url = _add_query_param(authorize_url, 'approval_prompt', 'force')
    return authorize_url

def get_code_from_url(url):
    """Extracts an authorization code from the query parameters of a url.

    This is part of the multi-step oauth process.
    When a user grants oauth access to this application, an authorization code
    is sent via a query parameter to our applications callback url. This code
    can be used to request an access token.

    Note that an authorization code is different from an access token.

    See google's oauth documentation for details:
    https://developers.google.com/accounts/docs/OAuth2
    """
    if url is None:
        raise ValueError('url must be a string')
    query_string = urlparse.urlparse(url)[4]
    query_params = urlparse.parse_qs(query_string)

    if 'error' in query_params:
        raise ValueError(query_params['error'])
    if not 'code' in query_params:
        raise ValueError('No code found')

    return query_params['code'][0]

def authorize_user_by_code(authorization_code, email):
    """Uses an authorization code to fetch an oauth access token.

    The access token is persisted to the database.

    This is the final step of the oauth process. See google's oauth
    documentation for details:
    https://developers.google.com/accounts/docs/OAuth2
    """
    flow = _get_flow()

    try:
        credentials = flow.step2_exchange(authorization_code)
    except oauth.FlowExchangeError as err:
        raise ValueError('Invalid authorization code: {}'.format(err))
    except oauth.Error as err:
        raise WebServiceError(err)

    try:
        _save_credentials(email, credentials)
    except PyMongoError as err:
        raise WebServiceError(err)

    return credentials.access_token

def delete_credentials(email, revoke=True):
    if revoke:
        try:
            _revoke_access(email)
        except WebServiceError:
            pass

    try:
        mongo.db.credentials.remove({'email': email})
    except PyMongoError as err:
        raise WebServiceError(err)

def _db_record_to_credentials(db_record):
    if 'credentials' not in db_record:
        return None

    credentials = oauth.OAuth2Credentials.from_json(json.dumps(db_record['credentials']))
    return credentials

def _save_credentials(email, credentials):
    db_record = _make_db_record(email, credentials)
    mongo.db.credentials.update({'email': email}, {'$set': db_record}, upsert=True)

def _make_db_record(email, credentials):
    record = {
        'email': email,
        'credentials': json.loads(credentials.to_json())
    }
    return record

def _get_credentials(email):
    try:
        result = mongo.db.credentials.find_one({'email': email})
    except PyMongoError as err:
        raise WebServiceError(err)

    if result is None:
        return None

    credentials = _db_record_to_credentials(result)
    return credentials   

def _add_query_param(url, key, value):
    scheme, netloc, path, query_string, fragment = urlparse.urlsplit(url)

    query_params = urlparse.parse_qs(query_string)
    query_params[key] = [value]
    query_string = urlencode(query_params, doseq=True)

    url = urlparse.urlunsplit((scheme, netloc, path, query_string, fragment))
    return url

def _get_flow():
    """Returns an OAuth2WebServerFlow instance, initialized from app.config
    """
    scope = ['https://www.googleapis.com/auth/cloudprint']
    flow = oauth.OAuth2WebServerFlow(
                    client_id=app.config['OAUTH_CLIENT_ID'],
                    client_secret=app.config['OAUTH_CLIENT_SECRET'],
                    redirect_uri=app.config['OAUTH_REDIRECT_URI'],
                    scope=scope)
    return flow

# TODO: handle if a user manually revokes us  
# (results in WebServiceError("Error revoking oauth token.") right now.)
def _revoke_access(email):
    """Revoke access to make the user connect their account again.
    """
    credentials = _get_credentials(email)
    if credentials is None:
        return None
    url = 'https://accounts.google.com/o/oauth2/revoke'
    post_data = {'token': credentials.access_token}
    try:
        response = requests.post(url, params=post_data)
    except requests.exceptions.ConnectionError as err:
        raise WebServiceError(err)
    except requests.exceptions.HTTPError as err:
        raise WebServiceError(err)
    except requests.exceptions.RequestException:
        raise WebServiceError(err)
    if response.status_code != 200:
        raise WebServiceError("Error revoking oauth token.")


class WebServiceError(Exception):
    pass
