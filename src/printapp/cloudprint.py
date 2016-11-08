# For more info, see https:#developers.google.com/cloud-print/docs/appInterfaces
import os
import json
import time
import client
import auth

CLOUDPRINT_URL = 'https://www.google.com/cloudprint'
UNIFLOW_ID = '7b30c56e-08f1-e90a-7fc8-ed11099a4a72'

def submit_job(token, file, color=False, duplex=False, copies=1, collate=True, staple=False):
    """Submits a print job to the uniFLOW printer.

    Token is an oauth token.
    File is a file-like object to be printed.
    Duplex means double sided.
    """
    file_name = os.path.basename(file.name)
    content = [file_name, file]
    oauth = auth.OAuth2(access_token=token, token_type='Bearer')
    print_ticket = _make_print_ticket(color=color, duplex=duplex, 
                                      copies=copies, collate=collate,
                                      staple=staple)
    try:
        job = client.submit_job(printer=UNIFLOW_ID, content=content, 
                                ticket=print_ticket, auth=oauth)
    except client.PrintingError as err:
        raise JobSubmissionError(err)

    if job.get('success', False) == False:
        raise JobSubmissionError('Error submitting the print job to Google.')

    try:
        job_id = job['job']['id']
    except KeyError as err:
        raise JobSubmissionError(err)

    _wait_for_job_processing(auth=oauth, job_id=job_id)


def has_uniflow_printer(token):
    """Returns True if the user has the Calvin uniFLOW printer installed
    on their Google account, and False otherwise.

        Params:
    token - oauth token.
    """
    # for use with 'fakeoauth.py' testing utility
    if token == 'fakeoauth.py':
        return True
    if token == 'fakeoauth.py|noprinter':
        return False

    oauth = auth.OAuth2(access_token=token, token_type='Bearer')
    printers = client.list_printers(auth=oauth)['printers']
    for printer in printers:
        id = printer.get('id')
        if id == UNIFLOW_ID:
            return True
    return False


def _make_print_ticket(color=False, duplex=False, copies=1, collate=True, staple=False):
    """Returns a CloudJobTicket implemented in JSON.
       
    A CloudJobTicket is a description of how a cloud job 
    (e.g. print job, scan job) should be handled by the cloud device. 
    Also known as CJT.

    https://developers.google.com/cloud-print/docs/cdd#cjt
    """
    if color:
        color = 'STANDARD_COLOR'
    else:
        color = 'STANDARD_MONOCHROME'
    if duplex:
        duplex = 2
    else:
        duplex = 0

    ticket = {

        'version': '1.0',
        'print': {

            'color': {
                'type': color
            },
            'duplex': {
                'type': duplex
            },
            'copies': {
                'copies': copies
            },
            'collate': {
                'collate': collate
            }
        }

    }

    if staple:
        ticket['print']['vendor_ticket_item'] = [
            {
                'id': 'psk:JobStapleAllDocuments',
                'value': 'psk:StapleTopLeft'
            }
        ]

    return json.dumps(ticket)


def _wait_for_job_processing(auth, job_id):
    """Check the print history to see if Google correctly processed
    the print job with corresponding 'job_id'.

        Params:
    auth - OAuth2 object
    job_id - string, id of print job.
    """
    time.sleep(1)
    error_free = False
    num_tried = 0
    while num_tried < 29 and error_free == False:
        time.sleep(1)
        num_tried += 1
        try:
            job_history = client.list_jobs(auth=auth)['jobs']
        except client.PrintingError as err:
            raise JobSubmissionError(err)
        except KeyError as err:
            raise JobSubmissionError(err)
        for job in job_history:
            try:
                id = job['id']
            except KeyError as err:
                raise JobSubmissionError(err)
            if id == job_id:
                if job.get('status', 'ERROR') == 'ERROR':
                    raise JobSubmissionError('Google could not correctly ' 
                                             + 'process the file submitted.')
                elif job.get('status') == 'DONE':
                    error_free = True
                    break


class JobSubmissionError(Exception):
    pass
