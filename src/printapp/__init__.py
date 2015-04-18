import os
from flask import Flask
from flask.ext.pymongo import PyMongo

app = Flask(__name__, static_url_path='/static')

app.config.from_object('printapp.config')
# The `PRINTAPP_SETTINGS` environment variable is the filename of a settings
# file which overrides the default settings.
app.config.from_envvar('PRINTAPP_SETTINGS', silent=True)

mongo = PyMongo(app)
with app.app_context():
    mongo.db.credentials.ensure_index('email')

import printapp.util
import printapp.routes
import printapp.api

import logging
from logging.handlers import RotatingFileHandler
file_handler = RotatingFileHandler(app.config['LOGFILE'], 'a', 1 * 1024 * 1024, 10)
file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
app.logger.setLevel(logging.INFO)
file_handler.setLevel(logging.INFO)
app.logger.addHandler(file_handler)

