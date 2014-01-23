__author__ = 'Daniel Alkemic Czuba <dc@danielczuba.pl>'

import os

PID_FILE = '/tmp/janitor.pid'
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SQLITE_FILE = 'janitor.db'
SQLITE_PATH = os.path.abspath(os.path.join(PROJECT_ROOT, 'data', SQLITE_FILE))

INTERVAL = 55
