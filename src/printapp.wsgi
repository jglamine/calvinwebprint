activate_this = '/var/www/printapp/venv/bin/activate_this.py'
execfile(activate_this, dict(__file__=activate_this))

import sys
import logging
import os
logging.basicConfig(stream=sys.stderr)
sys.path.insert(0,'/var/www/printapp/')

os.environ['PRINTAPP_MODE'] = 'production'

from printapp import app as application
