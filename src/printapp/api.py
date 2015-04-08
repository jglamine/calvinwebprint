from printapp import app, util
import printstatus
import cloudprint
import oauthcredentials
import document
import werkzeug
from flask import make_response, abort, session, request, redirect
import flask

@app.route('/api/login', methods=['POST'])
def login():
    """API endpoint to login.

    Saves email and password in the session cookie.

    Expects an email and password as POST data.
    Response body is empty.
    Response codes:
        200 - login successful
        400 - invalid request - missing email or password
        401 - invalid credentials
        504 - error connecting to uniflow
        502 - unexpected response from uniflow, the scraper is broken
    """
    session.clear()

    email = request.form.get('email')
    password = request.form.get('password')
    if email is None or password is None:
        abort(400)

    email = email.strip()
    try:
        username = email.split('@')[0]
    except IndexError:
        abort(401)

    try:
        printstatus.get_uniflow_client(username, password)
    except printstatus.InvalidCredentialsError:
        abort(401)
    except printstatus.NetworkError:
        abort(504)
    except printstatus.ScrapingError:
        abort(502)

    session['email'] = email
    session['password'] = password
    session.permanent = True

    return '', 200

@app.route('/api/logout', methods=['POST'])
def logout():
    """API endpoint to log out. Deletes the session cookie.

    Redirects to '/'
    """
    session.clear()
    return redirect('/')

@app.route('/api/cloudprintstatus', methods=['GET'])
def cloudprintstatus():
    """API endpoint with status concerning whether printing with cloudprint is possible.

    Response body is a JSON string.
    Response codes:
        200 - successful
        401 - invalid credentials
        504 - database error
    """
    try:
        email, password = util.get_current_user_credentials()
    except ValueError:
        abort(401)
    oauth_url = oauthcredentials.get_authentication_prompt_url(email)
    token_found = False
    printer_installed = None
    try:
        token = oauthcredentials.get_token(email)
    except oauthcredentials.WebServiceError:
        abort(504)

    if token is not None:
        token_found = True
        printer_installed = cloudprint.has_uniflow_printer(token)

    return flask.jsonify(haveCloudPrintPermission=token_found, 
                         isPrinterInstalled=printer_installed, 
                         cloudPrintPermissionUrl=oauth_url), 200


@app.route('/api/uniflowstatus', methods=['GET'])
def uniflowstatus():
    """API endpoint to get a user's print budget and print queue.

    Response body is JSON.
    Response codes:
        200 - budget and print queue retrieved successfully
        401 - invalid credentials
        504 - error connecting to uniflow
        502 - unexpected response from uniflow; the scraper is broken
    """
    try:
        email, password = util.get_current_user_credentials()
    except ValueError:
        abort(401)
    username = email.split('@')[0]
    
    try:
        uniflow = printstatus.get_uniflow_client(username, password)
        queue = uniflow.get_print_queue()
        budget = uniflow.get_budget()
    except printstatus.InvalidCredentialsError:
        abort(401)
    except printstatus.NetworkError:
        abort(504)
    except printstatus.ScrapingError:
        abort(502)

    jobs = []
    for job in queue:
        parsed_job = job._asdict()
        parsed_job['color'] = _is_color_job(job)
        jobs.append(parsed_job)
    
    response = {}
    response['queue'] = jobs
    response['budget'] = budget

    return flask.jsonify(**response), 200


@app.route('/api/upload', methods=['POST'])
def upload_file():
    '''API endpoint to upload a file to be printed.

    Expects file as POST data.
    Response body is the file_id of the saved file.
    Response codes:
        201 - upload successful
        400 - invalid request - missing file parameter or invalid file name
        401 - invalid credentials
        504 - database error
    '''
    try:
        email, password = util.get_current_user_credentials()
    except ValueError:
        abort(401)

    file_handle = request.files['file']
    if file_handle is None:
        abort(400)
    
    document_name = werkzeug.secure_filename(file_handle.filename)
    if not _has_supported_filetype(document_name):
        abort(400)
    try:
        document_id = document.save_document(file_handle, 
                                             document_name, email)
    except document.DatabaseError:
        abort(504)

    return flask.jsonify(file_id=document_id), 201


@app.route('/api/revokecloudprint', methods=['POST'])
def revoke_cloudprint():
    '''API endpoint to revoke cloud print oauth token.

    Response codes:
        401 - invalid credentials
        504 - database error
        200  - success
    '''
    try:
        email, password = util.get_current_user_credentials()
    except ValueError:
        abort(401)

    try:
        token = oauthcredentials.delete_credentials(email, revoke=True)
    except oauthcredentials.WebServiceError:
        abort(504)

    return '', 200


@app.route('/api/print', methods=['POST'])
def printjob():
    '''API endpoint to submit a print job.

    Example of JSON expected as POST data:
    {
        file_id: oid
        color: True
        double_sided: False
        collate: True
        copies: 3,
        staple: True
    }
    where oid is the string representation of the objectid returned by Mongo.

    Response body is empty.
    Response codes:
        201 - print job submission successful
        400 - invalid request - missing parameter(s) or file not found in database
        401 - invalid credentials
        409 - token not found
        504 - database error
        502 - error submitting job to Google
    '''
    try:
        file_id = request.form.get('file_id')
        copies = int(request.form.get('copies'))
        color = _parse_bool(request.form.get('color'))
        collate = _parse_bool(request.form.get('collate'))
        double_sided = _parse_bool(request.form.get('double_sided'))
        staple = _parse_bool(request.form.get('staple'))
    except ValueError:
        abort(400)
    if None in (file_id, copies, color, collate, double_sided, staple):
        abort(400, 'Missing required argument.')
    if copies < 1:
        abort(400, 'Cannot print fewer than 1 copy.')

    try:
        email, password = util.get_current_user_credentials()
    except ValueError:
        abort(401)

    try:
        token = oauthcredentials.get_token(email)
    except oauthcredentials.WebServiceError:
        abort(504)
    if token is None:
        abort(409)

    try:
        file_handle = document.get_document(file_id, email)
    except document.DatabaseError:
        abort(504)
    if file_handle is None:
        abort(400)

    try: 
        cloudprint.submit_job(token, file_handle, color=color, duplex=double_sided,
                              copies=copies, collate=collate, staple=staple)
    except cloudprint.JobSubmissionError:
        abort(502)
    finally:
        document.delete_document(file_id, email)

    file_handle.close()
    return '', 201

@app.route('/api/deletejob/<job_id>', methods=['POST'])
def deletejob(job_id):
    '''API endpoint to delete a print job.

    Response body is empty.
    Response codes:
        200 - print job deleted successfully
        400 - invalid request - missing print job id
        401 - invalid credentials
        504 - database error
        502 - scraping error
    '''
    if job_id is None:
        abort(400, 'Missing print job id.')

    try:
        email, password = util.get_current_user_credentials()
    except ValueError:
        abort(401)
    username = email.split('@')[0]
    
    try:
        uniflow = printstatus.get_uniflow_client(username, password)
        uniflow.delete_print_jobs([job_id])
    except printstatus.InvalidCredentialsError:
        abort(401)
    except printstatus.NetworkError:
        abort(504)
    except printstatus.ScrapingError:
        abort(502)
    return '', 200

def _parse_bool(string):
    if string is None:
        raise ValueError('None is not a valid boolean')

    string = string.lower()
    if string in ('true', 'yes', '1'):
        return True
    if string in ('false', 'no', '0'):
        return False
    raise ValueError('{} is not a valid boolean.'.format(string))

def _is_color_job(print_job):
    """Return True if the PrintJob is a color job.

    The price is used to determine whether or not it is a color job.

    Expects the Flask configuration to have a 'PRINTPRICES' setting:
        PRINTPRICES is a list of dictionaries which hold information on the 
        prices of printers.
            {
                'color': 0.2675,
                'black': 0.0245
            }

    The printer with the closest price match is used. Returns False if
    the 'PRINTPRICES' setting is missing.
    """
    price_per_page = print_job.price / float(print_job.pages * print_job.copies)
    prices = []
    print_prices = app.config.get('PRINTPRICES')
    if print_prices is None:
        return False

    for price_info in print_prices:
        prices.append((True, price_info['color']))
        prices.append((False, price_info['black']))
    
    return min(prices, key=lambda x: abs(price_per_page - x[1]))[0]


def _has_supported_filetype(filename):
    filename = filename.lower()
    return filename.rsplit('.', 1)[1] in ['txt', 'pdf', 'docx', 'doc', 'xps',
                                          'odt', 'png', 'jpg', 'jpeg', 'gif']
