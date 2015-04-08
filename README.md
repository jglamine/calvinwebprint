# Printing

A friendlier interface to the print system at Calvin College.

## Setup

Dependencies:

* python 2.7
* pip
* git
* mongodb

Clone the git repository. In the repo, create a virtual environment for Python:

    virtualenv venv

Every time you open a new terminal window, you will have to activate the virtual environment with:

    source venv/Scripts/activate

Install the python dependencies with:

    pip install -r requirements.txt

Run the development server with:

    python src/server.py debug

You can now view the website at `http://localhost:5001`

## Python package management with pip

Be sure to activate the python virtual environment. The list of required python packages is at `requirements.txt`. If you install a new python package with ``pip install <package name>``, be sure to update requirements.txt:

    pip freeze > requirements.txt

When pulling code changes from git, be sure to update your local packages from requirements.txt:

    pip install -r requirements.txt

## Configuration Settings

Default settings are loaded from `defaults.config`. To override these settings, create a configuration file and save the path to this file in the environment variable `PRINTAPP_SETTINGS`.

Add your cloudprint api keys to this custom configuration file. If you do not set the cloudprint keys, communication with google cloud print will not work.

## Developing without cloudprint API keys

Most developers will not have cloudprint API keys. This is fine, it just means you won't be able to use certain features such as submitting print jobs and connecting an account to cloudprint.

When cloudprint API keys are missing, relevant unit tests are disabled.

### Inserting fake credentials for testing purposes.
Use `fakeoauth.py` to add fake oauth credentials for your account. This will allow you to test additional parts of the front end, even without cloudprint API keys.

Add credentials:

    python fakeoauth.py <email>

Delete credentials:

    python fakeoauth.py <email> delete

Add credentials, and make the app think the uniFLOW printer is not connected to the account:

    python fakeoauth.py <email> noprinter

## Unit Testing

#### Loading Calvin ID credentials

Many of the tests require a valid Calvin student user name and password.
The tests load these credentials from environment variables.

You will create a shell script called `credentials.env` containing the following commands:

    export UNIFLOW_USER=your_username
    export UNIFLOW_PASSWORD=your_password

Be sure to grant oauth access to your cloud print account, as many of the tests will fail without it.

You may also want to add the path to a custom configuration file which overrides settings from `defaults.config`:

    export PRINTAPP_SETTINGS=/path/to/printapp.config

You can then load environment variables with the following command:

    source credentials.env

Like activating the virtual environment, you will have to run this command in each new bash session or terminal window that you open.

#### Using Nose to run tests
    
Run the tests with from the root directory of the repo:

    nosetests

To include the test which submits files to your uniFLOW print queue:

    nosetests --no-skip

If the command does not execute, make sure you load packages from requirements.txt

## Contributing

We are using [PEP08](http://legacy.python.org/dev/peps/pep-0008/) as our style guide. Public methods should have doc strings.
