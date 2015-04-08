from printapp import app, util
from flask import make_response, request, redirect
import oauthcredentials

@app.route('/')
def index():
    """Route for index.html, served statically.

    Also sets various cookies which the front end uses.
    """
    response = make_response(app.send_static_file('index.html'))

    # Set status cookies used by the front end.
    signed_in = True
    try:
        email, password = util.get_current_user_credentials()
    except ValueError:
        signed_in = False

    if signed_in:
        response.set_cookie('email', value=email)
        response.set_cookie('isAuthenticated', value='true')
    else:
        response.set_cookie('email')
        response.set_cookie('isAuthenticated')

    return response

@app.route('/help')
@app.route('/support')
def help():
    """Route for help.html, served statically.
    """
    response = make_response(app.send_static_file('help.html'))
    return response

@app.route('/oauthredirect')
def oauthredirect():
    """Callback route to receive an authorization code for cloud print.

    The code is used to request and save an oauth token for the current user.

    See `oauthcredentials.py` for details.
    """
    try:
        email, _ = util.get_current_user_credentials()
    except ValueError:
        return redirect('/')

    try:
        authorization_code = oauthcredentials.get_code_from_url(request.url)
    except ValueError:
        return redirect('/')

    try:
        oauthcredentials.authorize_user_by_code(authorization_code, email)
    except ValueError:
        return redirect('/')
    except oauthcredentials.WebServiceError:
        return redirect('/')
    return redirect('/')
